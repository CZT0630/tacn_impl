"""Agent 运行时抽象 - 编排层的调度目标."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.core.models import (
    CapabilityType,
    ExecutionPlan,
    SubTask,
    SubTaskResult,
)


class AgentRuntime(ABC):
    """Agent 运行时接口.

    编排层（OrchestrationEngine / MTCCOrchestrator）通过此接口调度 Agent，
    不依赖具体的 Agent 实现（LLMAgent / Claude SDK / LangGraph 等）。
    """

    @abstractmethod
    async def execute(
        self, subtask: SubTask, context: dict[str, Any] | None = None
    ) -> SubTaskResult:
        """执行单个子任务.

        Args:
            subtask: 子任务定义
            context: 执行上下文（上游结果、环境信息等）

        Returns:
            子任务执行结果
        """
        ...

    @abstractmethod
    async def execute_plan(self, plan: ExecutionPlan) -> dict[str, Any]:
        """执行整个计划（含并行组调度）.

        Args:
            plan: 完整执行计划

        Returns:
            执行摘要 {"status", "total_latency_ms", "total_cost", "results"}
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list[CapabilityType]:
        """声明当前 runtime 支持的能力列表."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """获取运行时统计信息（可选覆写）."""
        return {}


class MockAgentRuntime(AgentRuntime):
    """基于当前 LLMAgent mock 的运行时实现.

    包装现有 AgentManager，对外暴露 AgentRuntime 接口。
    """

    def __init__(self, registry):
        from backend.agent.factory import AgentManager

        self._manager = AgentManager(registry)
        self._manager.initialize()

    async def execute(
        self, subtask: SubTask, context: dict[str, Any] | None = None
    ) -> SubTaskResult:
        """执行单个子任务.

        根据 subtask 的 required_capabilities 找到匹配的 Agent 执行。
        """
        # 找到能执行此子任务的 Agent
        assignment = self._find_assignment(subtask)
        if assignment is None:
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id="",
                location=subtask.privacy_level.__class__.__name__,
                success=False,
                error=f"No agent found for subtask {subtask.name}",
            )
        return await self._manager.execute_subtask(assignment, subtask)

    async def execute_plan(self, plan: ExecutionPlan) -> dict[str, Any]:
        """执行整个计划."""
        return await self._manager.execute_plan(plan)

    def get_capabilities(self) -> list[CapabilityType]:
        """获取所有已注册 Agent 支持的能力."""
        caps = set()
        for profile in self._manager.registry.get_all_agents():
            for cap in profile.capabilities:
                caps.add(cap.capability_type)
        return list(caps)

    def get_stats(self) -> dict[str, Any]:
        """获取 Agent 统计信息."""
        return self._manager.get_agent_stats()

    def _find_assignment(self, subtask: SubTask) -> str | None:
        """为子任务找到最佳 Agent ID."""
        from backend.core.models import Location

        best_agent_id = None
        best_score = -1.0

        for profile in self._manager.registry.get_available_agents():
            score = 0.0
            if subtask.required_capabilities:
                for req in subtask.required_capabilities:
                    cap = profile.get_capability(req.capability_type)
                    if cap:
                        score += cap.quality
                score /= len(subtask.required_capabilities)
            else:
                score = 0.5  # 无能力需求时给默认分

            if score > best_score:
                best_score = score
                best_agent_id = profile.id

        return best_agent_id

    @property
    def manager(self):
        """暴露内部 AgentManager（用于向后兼容）."""
        return self._manager
