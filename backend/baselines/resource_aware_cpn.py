"""Resource-aware CPN基线 - 基于资源感知的传统调度."""

from __future__ import annotations

from typing import Any, Optional

from backend.core.models import (
    AgentAssignment,
    ExecutionPlan,
    Location,
)
from backend.parser.intent_parser import LLMIntentParser
from backend.parser.subtask_builder import LLMSubTaskBuilder
from backend.registry.agent_registry import AgentRegistry


class ResourceAwareCPN:
    """Resource-aware CPN基线.

    使用与TACN相同的意图解析和子任务分解，
    但路由仅基于资源负载，不考虑能力匹配。
    """

    def __init__(self, registry: AgentRegistry, llm_client: Any = None):
        self.registry = registry
        self.intent_parser = LLMIntentParser(llm_client)
        self.subtask_builder = LLMSubTaskBuilder(llm_client)

    async def process(self, request: str, deadline_ms: float = 30000) -> ExecutionPlan:
        # 1. LLM解析意图
        intent = await self.intent_parser.parse(request, deadline_ms)

        # 2. LLM分解子任务图
        subtask_graph = await self.subtask_builder.build(intent)

        # 3. 基于资源感知的调度：选择负载最低的Agent
        available_agents = self.registry.get_available_agents()
        assignments = []

        for subtask in subtask_graph.subtasks:
            if not available_agents:
                continue

            best_agent = min(available_agents, key=lambda a: a.current_load)
            estimated_latency = best_agent.avg_latency_ms + subtask.estimated_computation * 1.0
            estimated_cost = best_agent.cost_per_invocation + subtask.estimated_computation * 0.001

            assignments.append(AgentAssignment(
                subtask_id=subtask.id,
                agent_id=best_agent.id,
                location=best_agent.location,
                estimated_duration_ms=estimated_latency,
                estimated_cost=estimated_cost,
                priority=subtask.priority,
            ))

            best_agent.current_load = min(1.0, best_agent.current_load + 0.1)

        critical_path = self.subtask_builder.get_critical_path(subtask_graph)
        total_latency = sum(a.estimated_duration_ms for a in assignments)
        total_cost = sum(a.estimated_cost for a in assignments)

        return ExecutionPlan(
            task_id=intent.id,
            intent=intent,
            subtask_graph=subtask_graph,
            assignments=assignments,
            estimated_total_latency_ms=total_latency,
            estimated_total_cost=total_cost,
            critical_path=critical_path,
            metadata={"baseline": "resource_aware_cpn"},
        )
