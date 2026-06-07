"""Agent 工厂 — 根据 AgentProfile 创建 Agent 实例.

使用 ToolRegistry 统一管理工具，不再硬编码工具列表.
支持 HookRegistry 和 SkillLoader.
"""

from __future__ import annotations

import time
from typing import Optional

from backend.agent.base import BaseAgent
from backend.agent.terminal_agent import TerminalAgent
from backend.agent.peer_agent import PeerAgent
from backend.agent.edge_agent import EdgeAgent
from backend.agent.cloud_agent import CloudAgent
from backend.agent.message import MessageBus
from backend.agent.tools import ToolRegistry, create_default_tool_registry
from backend.core.models import AgentProfile, Location, SubTaskResult
from backend.registry.agent_registry import AgentRegistry


class AgentFactory:
    """Agent 工厂 — 根据 location 创建对应 Agent，注入 ToolRegistry + Hook + Skill."""

    def __init__(
        self,
        registry: AgentRegistry,
        llm_client=None,
        tool_registry: ToolRegistry | None = None,
        hooks=None,
        skill_loader=None,
    ):
        self.registry = registry
        self.llm_client = llm_client
        self.tool_registry = tool_registry or create_default_tool_registry()
        self.hooks = hooks
        self.skill_loader = skill_loader
        self.message_bus = MessageBus()
        self._agents: dict[str, BaseAgent] = {}

    def create_all_agents(self) -> dict[str, BaseAgent]:
        for profile in self.registry.get_all_agents():
            agent = self._create_agent(profile)
            self._agents[profile.id] = agent

        # 注入 delegate_task 工具到 edge/cloud agent
        self._inject_delegate_tool()

        return self._agents

    def _inject_delegate_tool(self):
        """为 edge/cloud agent 注入 delegate_task 工具."""
        from backend.agent.subagent import SubAgentManager
        llm_agents = {
            aid: a for aid, a in self._agents.items()
            if hasattr(a, '_dispatch')
        }
        if len(llm_agents) < 2:
            return
        subagent_mgr = SubAgentManager(llm_agents)
        for aid, agent in llm_agents.items():
            if agent.location in (Location.EDGE, Location.CLOUD):
                tool = subagent_mgr.create_delegate_tool(aid)
                agent._dispatch[tool.name] = tool
                if agent._openai_tools:
                    agent._openai_tools.append(tool.to_openai_tool())

    def _create_agent(self, profile: AgentProfile) -> BaseAgent:
        agent_map = {
            Location.TERMINAL: TerminalAgent,
            Location.PEER: PeerAgent,
            Location.EDGE: EdgeAgent,
            Location.CLOUD: CloudAgent,
        }
        agent_cls = agent_map.get(profile.location, TerminalAgent)
        return agent_cls(
            profile=profile,
            llm_client=self.llm_client,
            message_bus=self.message_bus,
            tool_registry=self.tool_registry,
            hooks=self.hooks,
            skill_loader=self.skill_loader,
        )

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_all_agents(self) -> dict[str, BaseAgent]:
        return self._agents.copy()


class AgentManager:
    """Agent 管理器."""

    def __init__(
        self,
        registry: AgentRegistry,
        llm_client=None,
        tool_registry: ToolRegistry | None = None,
        hooks=None,
        skill_loader=None,
    ):
        self.registry = registry
        self.factory = AgentFactory(
            registry, llm_client, tool_registry,
            hooks=hooks, skill_loader=skill_loader,
        )

    def initialize(self):
        self.factory.create_all_agents()

    async def execute_subtask(self, agent_id: str, subtask, context: dict | None = None) -> SubTaskResult:
        """用指定 Agent 执行子任务."""
        agent = self.factory.get_agent(agent_id)
        if not agent:
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=agent_id,
                location=Location.CLOUD,
                success=False,
                error=f"Agent {agent_id} not found",
            )
        return await agent.execute(subtask, context)

    async def execute_plan(self, plan) -> dict:
        """执行整个执行计划 — 支持并行组."""
        start = time.time()
        results = {}
        total_cost = 0.0

        if plan.parallel_groups:
            import asyncio
            for group in plan.parallel_groups:
                tasks = []
                group_items = []
                for subtask_id in group:
                    assignment = self._find_assignment(plan.assignments, subtask_id)
                    if assignment is None:
                        continue
                    subtask = plan.subtask_graph.get_subtask(subtask_id)
                    if subtask is None:
                        continue
                    context = self._build_context(plan, results, subtask_id)
                    tasks.append(self.execute_subtask(assignment.agent_id, subtask, context))
                    group_items.append((subtask_id, assignment))

                if tasks:
                    group_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for (subtask_id, assignment), result in zip(group_items, group_results):
                        if isinstance(result, Exception):
                            result = SubTaskResult(
                                subtask_id=subtask_id,
                                agent_id=assignment.agent_id,
                                location=assignment.location,
                                success=False,
                                error=str(result),
                            )
                        agent = self.factory.get_agent(assignment.agent_id)
                        results[subtask_id] = {
                            "success": result.success,
                            "agent_id": result.agent_id,
                            "agent_name": agent.name if agent else "Unknown",
                            "agent_type": type(agent).__name__.lower().replace("agent", "") if agent else "unknown",
                            "location": result.location.value,
                            "latency_ms": result.latency_ms,
                            "cost": result.cost,
                            "output": result.output,
                            "error": result.error,
                        }
                        total_cost += result.cost
        else:
            execution_order = [st.id for st in plan.subtask_graph.subtasks]
            for subtask_id in execution_order:
                assignment = self._find_assignment(plan.assignments, subtask_id)
                if assignment is None:
                    continue
                subtask = plan.subtask_graph.get_subtask(subtask_id)
                if subtask is None:
                    continue
                context = self._build_context(plan, results, subtask_id)
                result = await self.execute_subtask(assignment.agent_id, subtask, context)
                agent = self.factory.get_agent(assignment.agent_id)
                results[subtask_id] = {
                    "success": result.success,
                    "agent_id": result.agent_id,
                    "agent_name": agent.name if agent else "Unknown",
                    "agent_type": type(agent).__name__.lower().replace("agent", "") if agent else "unknown",
                    "location": result.location.value,
                    "latency_ms": result.latency_ms,
                    "cost": result.cost,
                    "output": result.output,
                    "error": result.error,
                }
                total_cost += result.cost

        total_latency_ms = (time.time() - start) * 1000
        all_success = all(r.get("success", False) for r in results.values())

        return {
            "status": "completed" if all_success else "failed",
            "total_latency_ms": total_latency_ms,
            "total_cost": total_cost,
            "results": results,
        }

    def _build_context(self, plan, results: dict, current_subtask_id: str) -> dict:
        upstream_results = {}
        predecessors = plan.subtask_graph.get_predecessors(current_subtask_id)
        for pred_id in predecessors:
            if pred_id in results:
                upstream_results[pred_id] = results[pred_id]
        return {"upstream_results": upstream_results} if upstream_results else {}

    def _find_assignment(self, assignments, subtask_id: str):
        for a in assignments:
            if a.subtask_id == subtask_id:
                return a
        return None

    def get_agent_stats(self) -> dict:
        stats = {}
        for agent_id, agent in self.factory.get_all_agents().items():
            profile = agent.profile
            stats[agent_id] = {
                "name": agent.name,
                "location": agent.location.value,
                "type": type(agent).__name__,
                "capabilities": [c.capability_type.value for c in profile.capabilities],
                "tools": list(agent._dispatch.keys()) if hasattr(agent, '_dispatch') else [],
                "current_load": profile.current_load,
                "avg_latency_ms": profile.avg_latency_ms,
                "privacy_level": profile.privacy_level.value,
            }
        return stats

    def get_system_topology(self) -> dict:
        topology = {"terminal": [], "peer": [], "edge": [], "cloud": []}
        for agent_id, agent in self.factory.get_all_agents().items():
            loc = agent.location.value
            if loc in topology:
                topology[loc].append({
                    "id": agent_id,
                    "name": agent.name,
                    "type": type(agent).__name__,
                })
        return topology
