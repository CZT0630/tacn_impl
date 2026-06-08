"""MTCC 联合编排器 - 模型-工具-算力-上下文联合编排."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field

from backend.core.models import (
    AgentProfile,
    CapabilityType,
    Location,
    PrivacyLevel,
    SubTask,
    SubTaskGraph,
)
from backend.infrastructure.network import NetworkModel
from backend.registry.agent_registry import AgentRegistry
from backend.registry.context_registry import ContextRegistry
from backend.registry.model_registry import ModelRegistry
from backend.registry.tool_registry import ToolRegistry


class MTCCDecision(BaseModel):
    """MTCC 联合决策结果."""

    subtask_id: str
    selected_agent_id: str
    selected_model: str
    selected_tools: list[str] = Field(default_factory=list)
    selected_context: list[str] = Field(default_factory=list)
    selected_compute_tier: Location = Location.EDGE
    privacy_action: str = "allow_remote"  # "local_only" | "anonymize" | "allow_remote"
    execution_mode: str = "direct"  # "direct" | "delegated" | "collaborative"
    estimated_latency_ms: float = 0.0
    estimated_cost: float = 0.0
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)


@dataclass
class MTCCConfig:
    """MTCC 编排配置."""

    capability_weight: float = 0.20
    model_quality_weight: float = 0.15
    tool_coverage_weight: float = 0.08
    context_relevance_weight: float = 0.08
    latency_weight: float = 0.12
    cost_weight: float = 0.08
    privacy_weight: float = 0.08
    reliability_weight: float = 0.12
    observed_quality_weight: float = 0.09
    location_preferences: dict[Location, float] = field(
        default_factory=lambda: {
            Location.TERMINAL: 0.9,
            Location.PEER: 0.8,
            Location.EDGE: 0.7,
            Location.CLOUD: 0.5,
        }
    )


PRIVACY_ORDER = {
    PrivacyLevel.PUBLIC: 0,
    PrivacyLevel.INTERNAL: 1,
    PrivacyLevel.CONFIDENTIAL: 2,
    PrivacyLevel.RESTRICTED: 3,
}


class MTCCOrchestrator:
    """模型-工具-算力-上下文联合编排器.

    为每个子任务同时决定:
    - selected_agent: 由哪个智能体执行
    - selected_model: 使用哪个模型
    - selected_tools: 调用哪些工具
    - selected_context: 使用哪些上下文源
    - selected_compute_tier: 在哪个计算层执行
    - privacy_action: 隐私处理方式
    - execution_mode: 执行模式
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        context_registry: ContextRegistry,
        network_model: NetworkModel,
        config: Optional[MTCCConfig] = None,
    ):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.context_registry = context_registry
        self.network_model = network_model
        self.config = config or MTCCConfig()

    def orchestrate_subtask(self, subtask: SubTask) -> Optional[MTCCDecision]:
        """为单个子任务做出 MTCC 联合决策."""
        candidates = self._get_candidate_agents(subtask)
        if not candidates:
            return None

        best_decision = None
        best_score = -1.0

        for agent in candidates:
            decision = self._evaluate_candidate(subtask, agent)
            if decision and decision.score > best_score:
                best_score = decision.score
                best_decision = decision

        return best_decision

    def orchestrate_graph(self, graph: SubTaskGraph) -> list[MTCCDecision]:
        """为整个子任务图做出 MTCC 联合决策."""
        decisions = []

        for subtask_id in graph.topological_sort():
            subtask = graph.get_subtask(subtask_id)
            if subtask is None:
                continue
            decision = self.orchestrate_subtask(subtask)
            if decision:
                decisions.append(decision)

        return decisions

    # ---- 内部方法 ----

    def _get_candidate_agents(self, subtask: SubTask) -> list[AgentProfile]:
        """筛选候选 Agent."""
        candidates = []
        for agent in self.agent_registry.get_available_agents():
            has_cap = any(
                agent.has_capability(req.capability_type)
                for req in subtask.required_capabilities
            )
            if not has_cap:
                continue
            # 隐私过滤
            agent_level = PRIVACY_ORDER.get(agent.privacy_level, 0)
            task_level = PRIVACY_ORDER.get(subtask.privacy_level, 0)
            if agent_level < task_level:
                continue
            candidates.append(agent)
        return candidates

    def _evaluate_candidate(
        self, subtask: SubTask, agent: AgentProfile
    ) -> Optional[MTCCDecision]:
        """评估一个候选 Agent 的 MTCC 组合."""
        selected_model = self._select_model(subtask, agent)
        selected_tools = self._select_tools(subtask, agent)
        selected_context = self._select_context(subtask, agent)
        compute_tier = agent.location
        privacy_action = self._decide_privacy(subtask, agent, compute_tier)
        execution_mode = self._determine_execution_mode(subtask, agent)

        scores = {}
        scores["capability"] = self._score_capability(subtask, agent)
        scores["model_quality"] = self._score_model_quality(subtask, selected_model)
        scores["tool_coverage"] = self._score_tool_coverage(subtask, selected_tools)
        scores["context_relevance"] = self._score_context_relevance(
            subtask, selected_context
        )
        scores["latency"] = self._score_latency(subtask, agent)
        scores["cost"] = self._score_cost(subtask, agent)
        scores["privacy"] = self._score_privacy(subtask, agent, privacy_action)
        # 反馈指标 — 来自 ExecutionFeedback 的长期观测
        scores["reliability"] = agent.reliability_score
        scores["observed_quality"] = (
            agent.tool_success_rate * 0.5 + agent.context_hit_rate * 0.5
        )

        cfg = self.config
        total_score = (
            scores["capability"] * cfg.capability_weight
            + scores["model_quality"] * cfg.model_quality_weight
            + scores["tool_coverage"] * cfg.tool_coverage_weight
            + scores["context_relevance"] * cfg.context_relevance_weight
            + scores["latency"] * cfg.latency_weight
            + scores["cost"] * cfg.cost_weight
            + scores["privacy"] * cfg.privacy_weight
            + scores["reliability"] * cfg.reliability_weight
            + scores["observed_quality"] * cfg.observed_quality_weight
        )
        total_score = min(1.0, total_score)

        estimated_latency = self._estimate_latency(subtask, agent)
        estimated_cost = self._estimate_cost(subtask, agent)

        return MTCCDecision(
            subtask_id=subtask.id,
            selected_agent_id=agent.id,
            selected_model=selected_model,
            selected_tools=selected_tools,
            selected_context=selected_context,
            selected_compute_tier=compute_tier,
            privacy_action=privacy_action,
            execution_mode=execution_mode,
            estimated_latency_ms=estimated_latency,
            estimated_cost=estimated_cost,
            score=total_score,
            score_breakdown=scores,
        )

    def _select_model(self, subtask: SubTask, agent: AgentProfile) -> str:
        if agent.default_model:
            return agent.default_model
        if agent.supported_models:
            return agent.supported_models[0]
        return "default"

    def _select_tools(self, subtask: SubTask, agent: AgentProfile) -> list[str]:
        return [t for t in subtask.required_tools if t in agent.tools]

    def _select_context(self, subtask: SubTask, agent: AgentProfile) -> list[str]:
        return [c for c in subtask.required_context if c in agent.context_access]

    def _decide_privacy(
        self, subtask: SubTask, agent: AgentProfile, compute_tier: Location
    ) -> str:
        if subtask.privacy_level == PrivacyLevel.RESTRICTED:
            return "local_only"
        if (
            subtask.privacy_level == PrivacyLevel.CONFIDENTIAL
            and compute_tier == Location.CLOUD
        ):
            return "anonymize"
        return "allow_remote"

    def _determine_execution_mode(
        self, subtask: SubTask, agent: AgentProfile
    ) -> str:
        if len(subtask.required_capabilities) > 2:
            return "collaborative"
        return "direct"

    def _score_capability(self, subtask: SubTask, agent: AgentProfile) -> float:
        if not subtask.required_capabilities:
            return 0.5
        scores = []
        for req in subtask.required_capabilities:
            cap = agent.get_capability(req.capability_type)
            if cap is None:
                scores.append(0.0)
            else:
                scores.append(
                    1.0
                    if cap.quality >= req.min_quality
                    else cap.quality / req.min_quality
                )
        return sum(scores) / len(scores)

    def _score_model_quality(self, subtask: SubTask, model_id: str) -> float:
        model = self.model_registry.get_model(model_id)
        if not model:
            return 0.5
        return model.quality_scores.get(subtask.name, 0.5)

    def _score_tool_coverage(
        self, subtask: SubTask, selected_tools: list[str]
    ) -> float:
        if not subtask.required_tools:
            return 1.0
        return len(selected_tools) / len(subtask.required_tools)

    def _score_context_relevance(
        self, subtask: SubTask, selected_context: list[str]
    ) -> float:
        if not subtask.required_context:
            return 1.0
        return len(selected_context) / len(subtask.required_context)

    def _score_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        estimated = self._estimate_latency(subtask, agent)
        return max(0.0, 1.0 - estimated / 10000)

    def _score_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        estimated = self._estimate_cost(subtask, agent)
        return max(0.0, 1.0 - estimated)

    def _score_privacy(
        self, subtask: SubTask, agent: AgentProfile, action: str
    ) -> float:
        if action == "local_only":
            return 1.0
        if action == "anonymize":
            return 0.7
        return 0.5

    def _estimate_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        base = agent.avg_latency_ms
        compute = subtask.estimated_computation * 0.5
        data = subtask.estimated_data_size_kb * 0.01
        network = self.network_model.get_latency(Location.TERMINAL, agent.location)
        return base + compute + data + network

    def _estimate_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        return agent.cost_per_invocation + subtask.estimated_computation * 0.001
