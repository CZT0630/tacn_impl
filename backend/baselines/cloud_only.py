"""Cloud-only基线 - 所有任务都路由到云端."""

from __future__ import annotations

from typing import Any, Optional

from backend.core.models import (
    AgentAssignment,
    ExecutionPlan,
    Intent,
    Location,
)
from backend.parser.intent_parser import LLMIntentParser
from backend.parser.subtask_builder import LLMSubTaskBuilder
from backend.registry.agent_registry import AgentRegistry


class CloudOnlyBaseline:
    """Cloud-only基线.

    使用与TACN相同的意图解析和子任务分解，
    但所有子任务都路由到云端Agent。
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

        # 3. 获取云端Agent
        cloud_agents = self.registry.get_agents_by_location(Location.CLOUD)
        cloud_agent = cloud_agents[0] if cloud_agents else None

        # 4. 所有子任务都路由到云端
        assignments = []
        if cloud_agent:
            for subtask in subtask_graph.subtasks:
                estimated_latency = cloud_agent.avg_latency_ms + subtask.estimated_computation * 2 + 200
                estimated_cost = cloud_agent.cost_per_invocation + subtask.estimated_computation * 0.002
                assignments.append(AgentAssignment(
                    subtask_id=subtask.id,
                    agent_id=cloud_agent.id,
                    location=Location.CLOUD,
                    estimated_duration_ms=estimated_latency,
                    estimated_cost=estimated_cost,
                    priority=subtask.priority,
                ))

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
            metadata={"baseline": "cloud_only"},
        )
