"""执行反馈与闭环更新 - 驱动双闭环优化.

双闭环:
1. 资源-能力优化环: 执行后更新 Agent 的 reliability / latency / tool_success / context_hit
2. 意图-服务优化环: 按 intent_type 聚合统计，驱动 deadline 自适应 + 能力推断权重调整
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.core.models import TaskResult, ExecutionPlan
from backend.registry.agent_registry import AgentRegistry
from backend.registry.model_registry import ModelRegistry
from backend.registry.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class IntentPolicy:
    """某类意图的服务策略 — 由反馈闭环持续更新.

    Attributes:
        avg_latency_ms: 该意图类型的平均执行时延 (EMA)
        p95_latency_ms: 该意图类型的 P95 时延估计
        success_rate: 成功率 (EMA)
        suggested_deadline_ms: 建议的截止时间 (avg + 2*std 的上界)
        execution_count: 累计执行次数
    """
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    success_rate: float = 1.0
    suggested_deadline_ms: float = 30000.0
    execution_count: int = 0
    _latency_sq_avg: float = 0.0  # 用于计算方差


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
        # 意图-服务优化环: 按 intent_type 维护策略
        self._intent_policies: dict[str, IntentPolicy] = {}

    # ========================================================================
    # 资源-能力优化环
    # ========================================================================

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

        # 同步触发意图-服务策略更新
        intent_type = plan.intent.intent_type.value
        self.update_service_policy(intent_type, result)

    # ========================================================================
    # 意图-服务优化环
    # ========================================================================

    def update_service_policy(self, intent_type: str, result: TaskResult):
        """更新服务策略 (意图-服务优化环).

        根据执行结果调整该意图类型的服务策略:
        - 成功率 EMA
        - 平均时延 EMA
        - P95 时延估计 (基于均值+2*标准差)
        - 建议 deadline (P95 上界)
        """
        policy = self._get_or_create_policy(intent_type)
        policy.execution_count += 1

        # 成功率 EMA
        policy.success_rate = (
            self.ALPHA * (1.0 if result.success else 0.0)
            + (1 - self.ALPHA) * policy.success_rate
        )

        # 时延 EMA + 方差估计 (Welford 在线算法的 EMA 近似)
        latency = result.actual_latency_ms
        policy.avg_latency_ms = (
            self.ALPHA * latency + (1 - self.ALPHA) * policy.avg_latency_ms
        )
        policy._latency_sq_avg = (
            self.ALPHA * (latency ** 2) + (1 - self.ALPHA) * policy._latency_sq_avg
        )

        # P95 ≈ avg + 2*std (正态近似)
        variance = max(0.0, policy._latency_sq_avg - policy.avg_latency_ms ** 2)
        std = variance ** 0.5
        policy.p95_latency_ms = policy.avg_latency_ms + 2 * std

        # 建议 deadline: P95 + 20% 余量，下限 5s
        policy.suggested_deadline_ms = max(5000.0, policy.p95_latency_ms * 1.2)

        logger.debug(
            f"IntentPolicy[{intent_type}] updated: "
            f"success_rate={policy.success_rate:.2f}, "
            f"avg_latency={policy.avg_latency_ms:.0f}ms, "
            f"p95_latency={policy.p95_latency_ms:.0f}ms, "
            f"suggested_deadline={policy.suggested_deadline_ms:.0f}ms"
        )

    def get_intent_policy(self, intent_type: str) -> IntentPolicy | None:
        """获取某意图类型的服务策略."""
        return self._intent_policies.get(intent_type)

    def get_suggested_deadline(self, intent_type: str) -> float | None:
        """获取建议 deadline (仅在有足够样本时返回)."""
        policy = self._intent_policies.get(intent_type)
        if policy is None or policy.execution_count < 3:
            return None
        return policy.suggested_deadline_ms

    def _get_or_create_policy(self, intent_type: str) -> IntentPolicy:
        if intent_type not in self._intent_policies:
            self._intent_policies[intent_type] = IntentPolicy()
        return self._intent_policies[intent_type]

    # ========================================================================
    # 综合评分 & 统计
    # ========================================================================

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
        stats = {
            "total_executions": self._execution_count,
            "total_successes": self._success_count,
            "overall_success_rate": (
                self._success_count / self._execution_count
                if self._execution_count > 0
                else 0.0
            ),
            "intent_policies": {},
        }
        for intent_type, policy in self._intent_policies.items():
            stats["intent_policies"][intent_type] = {
                "execution_count": policy.execution_count,
                "success_rate": round(policy.success_rate, 3),
                "avg_latency_ms": round(policy.avg_latency_ms, 1),
                "p95_latency_ms": round(policy.p95_latency_ms, 1),
                "suggested_deadline_ms": round(policy.suggested_deadline_ms, 1),
            }
        return stats
