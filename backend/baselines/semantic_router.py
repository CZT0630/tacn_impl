"""Semantic-only基线 - 仅基于语义匹配."""

from __future__ import annotations

from typing import Any, Optional

from backend.core.models import (
    AgentAssignment,
    ExecutionPlan,
)
from backend.parser.intent_parser import LLMIntentParser
from backend.parser.subtask_builder import LLMSubTaskBuilder
from backend.registry.agent_registry import AgentRegistry


class SemanticOnlyRouter:
    """Semantic-only基线.

    使用与TACN相同的意图解析和子任务分解，
    但路由仅基于能力语义匹配，不考虑延迟、成本、隐私、负载。
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

        # 3. 仅基于语义匹配
        available_agents = self.registry.get_available_agents()
        assignments = []

        for subtask in subtask_graph.subtasks:
            best_agent = self._find_best_match(subtask, available_agents)
            if best_agent:
                estimated_latency = best_agent.avg_latency_ms + subtask.estimated_computation * 1.5
                estimated_cost = best_agent.cost_per_invocation + subtask.estimated_computation * 0.001
                assignments.append(AgentAssignment(
                    subtask_id=subtask.id,
                    agent_id=best_agent.id,
                    location=best_agent.location,
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
            metadata={"baseline": "semantic_only"},
        )

    def _find_best_match(self, subtask, available_agents):
        """找到能力匹配度最高的Agent."""
        best_agent = None
        best_score = -1

        for agent in available_agents:
            score = 0.0
            if subtask.required_capabilities:
                for req in subtask.required_capabilities:
                    cap = agent.get_capability(req.capability_type)
                    if cap:
                        score += cap.quality
                score /= len(subtask.required_capabilities)

            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent
