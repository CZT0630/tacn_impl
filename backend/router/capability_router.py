"""智能体能力路由器 - 基于多准则匹配将子任务路由到智能体."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.core.models import (
    AgentAssignment,
    AgentMatchResult,
    AgentProfile,
    Location,
    PrivacyLevel,
    SubTask,
    SubTaskGraph,
)
from backend.registry.agent_registry import AgentRegistry


@dataclass
class RoutingConfig:
    """路由配置."""
    capability_weight: float = 0.30
    latency_weight: float = 0.20
    cost_weight: float = 0.10
    privacy_weight: float = 0.10
    load_weight: float = 0.08
    reliability_weight: float = 0.12
    observed_quality_weight: float = 0.10

    location_preferences: dict[Location, float] = field(default_factory=lambda: {
        Location.TERMINAL: 0.9,
        Location.PEER: 0.8,
        Location.EDGE: 0.7,
        Location.CLOUD: 0.5,
    })

    max_acceptable_latency_ms: float = 10000
    max_acceptable_cost: float = 1.0
    enforce_privacy: bool = True


class AgentCapabilityRouter:
    """智能体能力路由器.

    基于多准则匹配将子任务路由到合适的智能体.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: Optional[RoutingConfig] = None,
    ):
        self.registry = registry
        self.config = config or RoutingConfig()

    def route_subtask(
        self,
        subtask: SubTask,
        available_agents: Optional[list[AgentProfile]] = None,
    ) -> Optional[AgentMatchResult]:
        """为子任务找到最佳智能体.

        Args:
            subtask: 子任务
            available_agents: 可用智能体列表

        Returns:
            最佳匹配结果，如果没有合适智能体则返回None
        """
        if available_agents is None:
            available_agents = self.registry.get_available_agents()

        candidates = self._filter_candidates(subtask, available_agents)
        if not candidates:
            return None

        matches: list[AgentMatchResult] = []
        for agent in candidates:
            match = self._score_agent(subtask, agent)
            if match.score > 0:
                matches.append(match)

        if not matches:
            return None

        return max(matches, key=lambda m: m.score)

    def route_subtask_graph(self, graph: SubTaskGraph) -> list[AgentAssignment]:
        """路由子任务图中的所有子任务.

        Args:
            graph: 子任务图

        Returns:
            智能体分配列表
        """
        assignments: list[AgentAssignment] = []
        agent_load: dict[str, float] = {}

        topo_order = graph.topological_sort()

        for subtask_id in topo_order:
            subtask = graph.get_subtask(subtask_id)
            if subtask is None:
                continue

            available_agents = self._get_agents_with_available_capacity(agent_load)
            match = self.route_subtask(subtask, available_agents)

            if match is None:
                match = self.route_subtask(subtask)

            if match is not None:
                agent = self.registry.get_agent(match.agent_id)
                if agent is not None:
                    assignment = AgentAssignment(
                        subtask_id=subtask.id,
                        agent_id=match.agent_id,
                        location=agent.location,
                        estimated_duration_ms=match.estimated_latency_ms,
                        estimated_cost=match.estimated_cost,
                        priority=subtask.priority,
                    )
                    assignments.append(assignment)

                    if match.agent_id not in agent_load:
                        agent_load[match.agent_id] = 0.0
                    agent_load[match.agent_id] += subtask.estimated_computation * 0.01

        return assignments

    def _filter_candidates(
        self,
        subtask: SubTask,
        agents: list[AgentProfile],
    ) -> list[AgentProfile]:
        """筛选候选智能体."""
        candidates = []

        for agent in agents:
            if not agent.is_available():
                continue

            if self.config.enforce_privacy:
                if not self._check_privacy_compatibility(subtask, agent):
                    continue

            has_capability = any(
                agent.has_capability(req.capability_type)
                for req in subtask.required_capabilities
            )
            if not has_capability:
                continue

            if subtask.required_tools:
                has_tools = any(tool in agent.tools for tool in subtask.required_tools)
                if not has_tools:
                    continue

            candidates.append(agent)

        return candidates

    def _check_privacy_compatibility(
        self, subtask: SubTask, agent: AgentProfile
    ) -> bool:
        """检查隐私兼容性."""
        privacy_order = {
            PrivacyLevel.PUBLIC: 0,
            PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2,
        }

        subtask_level = privacy_order.get(subtask.privacy_level, 0)
        agent_level = privacy_order.get(agent.privacy_level, 0)

        return agent_level >= subtask_level

    def _score_agent(self, subtask: SubTask, agent: AgentProfile) -> AgentMatchResult:
        """为智能体评分 — 包含反馈指标（可靠性、观测质量）."""
        scores: dict[str, float] = {}

        scores["capability"] = self._score_capability(subtask, agent)
        scores["latency"] = self._score_latency(subtask, agent)
        scores["cost"] = self._score_cost(subtask, agent)
        scores["privacy"] = self._score_privacy(subtask, agent)
        scores["load"] = self._score_load(agent)
        scores["location"] = self._score_location(agent)
        scores["reliability"] = agent.reliability_score
        scores["observed_quality"] = (
            agent.tool_success_rate * 0.5 + agent.context_hit_rate * 0.5
        )

        total_score = (
            scores["capability"] * self.config.capability_weight
            + scores["latency"] * self.config.latency_weight
            + scores["cost"] * self.config.cost_weight
            + scores["privacy"] * self.config.privacy_weight
            + scores["load"] * self.config.load_weight
            + scores["location"] * 0.05
            + scores["reliability"] * self.config.reliability_weight
            + scores["observed_quality"] * self.config.observed_quality_weight
        )

        # 确保分数不超过1.0
        total_score = min(1.0, total_score)

        estimated_latency = self._estimate_latency(subtask, agent)
        estimated_cost = self._estimate_cost(subtask, agent)

        latency_ok = estimated_latency <= self.config.max_acceptable_latency_ms
        cost_ok = estimated_cost <= self.config.max_acceptable_cost
        privacy_ok = self._check_privacy_compatibility(subtask, agent)

        if not latency_ok:
            total_score *= 0.5
        if not cost_ok:
            total_score *= 0.7
        if not privacy_ok:
            total_score = 0.0

        return AgentMatchResult(
            subtask_id=subtask.id,
            agent_id=agent.id,
            score=total_score,
            capability_coverage=scores["capability"],
            estimated_latency_ms=estimated_latency,
            estimated_cost=estimated_cost,
            privacy_satisfied=privacy_ok,
            breakdown=scores,
        )

    def _score_capability(self, subtask: SubTask, agent: AgentProfile) -> float:
        """评分: 能力覆盖."""
        if not subtask.required_capabilities:
            return 0.5

        coverage_scores = []
        for req in subtask.required_capabilities:
            cap = agent.get_capability(req.capability_type)
            if cap is None:
                coverage_scores.append(0.0)
            else:
                quality_score = 1.0 if cap.quality >= req.min_quality else cap.quality / req.min_quality
                coverage_scores.append(quality_score)

        return sum(coverage_scores) / len(coverage_scores)

    def _score_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        """评分: 延迟."""
        estimated = self._estimate_latency(subtask, agent)
        if estimated == 0:
            return 1.0
        score = 1.0 - min(1.0, estimated / self.config.max_acceptable_latency_ms)
        return max(0.0, score)

    def _score_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        """评分: 成本."""
        estimated = self._estimate_cost(subtask, agent)
        if estimated == 0:
            return 1.0
        score = 1.0 - min(1.0, estimated / self.config.max_acceptable_cost)
        return max(0.0, score)

    def _score_privacy(self, subtask: SubTask, agent: AgentProfile) -> float:
        """评分: 隐私."""
        return 1.0 if self._check_privacy_compatibility(subtask, agent) else 0.0

    def _score_load(self, agent: AgentProfile) -> float:
        """评分: 负载."""
        return agent.get_available_capacity()

    def _score_location(self, agent: AgentProfile) -> float:
        """评分: 位置."""
        return self.config.location_preferences.get(agent.location, 0.5)

    def _estimate_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        """估算延迟."""
        base_latency = agent.avg_latency_ms
        computation_time = subtask.estimated_computation * 0.5
        data_transfer_time = subtask.estimated_data_size_kb * 0.01
        network_latency = {
            Location.TERMINAL: 5,
            Location.PEER: 20,
            Location.EDGE: 50,
            Location.CLOUD: 150,
        }.get(agent.location, 50)

        return base_latency + computation_time + data_transfer_time + network_latency

    def _estimate_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        """估算成本."""
        base_cost = agent.cost_per_invocation
        computation_cost = subtask.estimated_computation * 0.001
        data_cost = subtask.estimated_data_size_kb * 0.0001
        return base_cost + computation_cost + data_cost

    def _get_agents_with_available_capacity(
        self, current_load: dict[str, float]
    ) -> list[AgentProfile]:
        """获取有可用容量的智能体."""
        available = []
        for agent in self.registry.get_all_agents():
            current = current_load.get(agent.id, 0.0)
            capacity = agent.get_available_capacity()
            if capacity > current:
                available.append(agent)
        return available

    def get_routing_statistics(self, assignments: list[AgentAssignment]) -> dict:
        """获取路由统计信息."""
        if not assignments:
            return {"total_assignments": 0}

        location_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}

        for assignment in assignments:
            loc = assignment.location.value
            location_counts[loc] = location_counts.get(loc, 0) + 1
            agent_counts[assignment.agent_id] = agent_counts.get(assignment.agent_id, 0) + 1

        total_cost = sum(a.estimated_cost for a in assignments)
        total_latency = sum(a.estimated_duration_ms for a in assignments)

        return {
            "total_assignments": len(assignments),
            "by_location": location_counts,
            "agents_used": len(agent_counts),
            "total_estimated_cost": total_cost,
            "total_estimated_latency_ms": total_latency,
        }
