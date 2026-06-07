"""执行反馈与闭环更新 - 驱动双闭环优化."""

from __future__ import annotations

from backend.core.models import TaskResult, ExecutionPlan
from backend.registry.agent_registry import AgentRegistry
from backend.registry.model_registry import ModelRegistry
from backend.registry.tool_registry import ToolRegistry


class ExecutionFeedback:
    """执行反馈 - 驱动双闭环优化.

    资源-能力优化环:
    资源感知 → Agent 能力建模 → MTCC 编排 → 协作执行反馈 → 资源与能力状态更新

    意图-服务优化环:
    用户意图 → 意图解析 → 任务图 → Agent 能力匹配 → 多 Agent 协作执行
    → 结果交付 → 用户反馈与服务策略更新
    """

    ALPHA = 0.1  # 指数移动平均系数

    def __init__(
        self,
        agent_registry: AgentRegistry,
        model_registry: ModelRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self._execution_count: int = 0
        self._success_count: int = 0

    def update_after_execution(self, result: TaskResult, plan: ExecutionPlan):
        """执行后更新资源-能力状态 (资源-能力优化环).

        更新内容:
        - Agent reliability_score
        - Agent observed_latency_ms
        - Agent tool_success_rate
        - Agent context_hit_rate
        - Agent routing_score
        """
        self._execution_count += 1
        if result.success:
            self._success_count += 1

        for subtask_id, sr in result.subtask_results.items():
            if not isinstance(sr, dict):
                continue
            agent_id = sr.get("agent_id")
            agent = self.agent_registry.get_agent(agent_id)
            if agent is None:
                continue

            success = sr.get("success", False)
            actual_latency = sr.get("latency_ms", 0)

            # 更新可靠性 (指数移动平均)
            agent.reliability_score = (
                self.ALPHA * (1.0 if success else 0.0)
                + (1 - self.ALPHA) * agent.reliability_score
            )

            # 更新观测时延
            agent.observed_latency_ms = (
                self.ALPHA * actual_latency
                + (1 - self.ALPHA) * agent.observed_latency_ms
            )

            # 更新工具成功率
            tool_success = sr.get("tool_success", success)
            agent.tool_success_rate = (
                self.ALPHA * (1.0 if tool_success else 0.0)
                + (1 - self.ALPHA) * agent.tool_success_rate
            )

            # 更新上下文命中率
            context_hit = sr.get("context_hit", False)
            agent.context_hit_rate = (
                self.ALPHA * (1.0 if context_hit else 0.0)
                + (1 - self.ALPHA) * agent.context_hit_rate
            )

            # 更新路由评分
            agent.routing_score = self._calculate_routing_score(agent)

    def update_service_policy(self, intent_type, result: TaskResult):
        """更新服务策略 (意图-服务优化环).

        根据执行结果调整该意图类型的服务策略.
        """
        # 记录成功/失败模式，可用于后续意图解析的策略调整
        pass

    def _calculate_routing_score(self, agent) -> float:
        """计算综合路由评分."""
        return (
            0.3 * agent.reliability_score
            + 0.2 * max(0.0, 1.0 - agent.observed_latency_ms / 10000)
            + 0.2 * agent.tool_success_rate
            + 0.15 * agent.context_hit_rate
            + 0.15 * agent.get_available_capacity()
        )

    def get_statistics(self) -> dict:
        """获取反馈统计信息."""
        return {
            "total_executions": self._execution_count,
            "total_successes": self._success_count,
            "overall_success_rate": (
                self._success_count / self._execution_count
                if self._execution_count > 0
                else 0.0
            ),
        }
