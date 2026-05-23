"""Agent工厂 - 根据AgentProfile创建Agent实例."""

from __future__ import annotations

import time
from typing import Optional

from backend.agent.base import BaseAgent
from backend.agent.terminal_agent import TerminalAgent
from backend.agent.peer_agent import PeerAgent
from backend.agent.edge_agent import EdgeAgent
from backend.agent.cloud_agent import CloudAgent
from backend.agent.message import MessageBus
from backend.core.models import AgentProfile, Location, SubTaskResult
from backend.registry.agent_registry import AgentRegistry


class AgentFactory:
    """Agent工厂.

    根据Agent的location自动创建对应的Agent实例.
    所有Agent共享同一个MessageBus.
    """

    def __init__(self, registry: AgentRegistry, llm_client=None):
        self.registry = registry
        self.llm_client = llm_client
        self.message_bus = MessageBus()
        self._agents: dict[str, BaseAgent] = {}

    def create_all_agents(self) -> dict[str, BaseAgent]:
        """创建所有注册的Agent实例."""
        for profile in self.registry.get_all_agents():
            agent = self._create_agent(profile)
            self._agents[profile.id] = agent
        return self._agents

    def _create_agent(self, profile: AgentProfile) -> BaseAgent:
        """根据location创建对应类型的Agent."""
        agent_map = {
            Location.TERMINAL: TerminalAgent,
            Location.PEER: PeerAgent,
            Location.EDGE: EdgeAgent,
            Location.CLOUD: CloudAgent,
        }
        agent_cls = agent_map.get(profile.location, TerminalAgent)
        return agent_cls(profile, self.llm_client, self.message_bus)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_all_agents(self) -> dict[str, BaseAgent]:
        return self._agents.copy()


class AgentManager:
    """Agent管理器.

    提供高级的Agent管理和执行功能.
    """

    def __init__(self, registry: AgentRegistry, llm_client=None):
        self.registry = registry
        self.factory = AgentFactory(registry, llm_client)

    def initialize(self):
        self.factory.create_all_agents()

    async def execute_subtask(self, agent_id: str, subtask) -> SubTaskResult:
        """用指定Agent执行子任务."""
        agent = self.factory.get_agent(agent_id)
        if not agent:
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=agent_id,
                location=Location.CLOUD,
                success=False,
                error=f"Agent {agent_id} not found",
            )
        return await agent.execute(subtask)

    async def execute_plan(self, plan) -> dict:
        """执行整个执行计划.

        Args:
            plan: ExecutionPlan

        Returns:
            执行结果摘要
        """
        start = time.time()
        results = {}
        total_cost = 0.0

        # 按并行组或拓扑顺序执行
        if plan.parallel_groups:
            execution_order = []
            for group in plan.parallel_groups:
                execution_order.extend(group)
        else:
            execution_order = [st.id for st in plan.subtask_graph.subtasks]

        for subtask_id in execution_order:
            assignment = None
            for a in plan.assignments:
                if a.subtask_id == subtask_id:
                    assignment = a
                    break
            if assignment is None:
                continue

            subtask = plan.subtask_graph.get_subtask(subtask_id)
            if subtask is None:
                continue

            result = await self.execute_subtask(assignment.agent_id, subtask)
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

    def get_agent_stats(self) -> dict:
        """获取所有Agent的统计信息."""
        stats = {}
        for agent_id, agent in self.factory.get_all_agents().items():
            profile = agent.profile
            stats[agent_id] = {
                "name": agent.name,
                "location": agent.location.value,
                "type": type(agent).__name__,
                "capabilities": [c.capability_type.value for c in profile.capabilities],
                "tools": profile.tools,
                "current_load": profile.current_load,
                "avg_latency_ms": profile.avg_latency_ms,
                "privacy_level": profile.privacy_level.value,
            }
        return stats

    def get_system_topology(self) -> dict:
        """获取系统拓扑."""
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
