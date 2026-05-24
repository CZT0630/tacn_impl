"""模型注册表."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    """模型画像."""

    id: str
    name: str
    model_type: str  # "lightweight", "vision", "rag", "llm"
    parameter_size: str = ""  # "1B", "7B", "70B"
    supported_tasks: list[str] = Field(default_factory=list)
    avg_latency_ms: float = 100.0
    cost_per_1k_tokens: float = 0.0
    quality_scores: dict[str, float] = Field(default_factory=dict)  # task_type -> quality
    max_context_length: int = 4096
    supports_tool_calling: bool = False
    metadata: dict = Field(default_factory=dict)


class ModelRegistry:
    """模型注册表.

    维护所有可用模型的画像，支持按任务类型/质量/成本查询.
    """

    def __init__(self):
        self._models: dict[str, ModelProfile] = {}

    def register(self, model: ModelProfile):
        """注册模型."""
        self._models[model.id] = model

    def unregister(self, model_id: str) -> bool:
        """注销模型."""
        return self._models.pop(model_id, None) is not None

    def get_model(self, model_id: str) -> Optional[ModelProfile]:
        """获取模型."""
        return self._models.get(model_id)

    def get_all_models(self) -> list[ModelProfile]:
        """获取所有模型."""
        return list(self._models.values())

    def find_models_for_task(self, task_type: str) -> list[ModelProfile]:
        """查找支持指定任务类型的模型."""
        return [m for m in self._models.values() if task_type in m.supported_tasks]

    def get_best_model(
        self,
        task_type: str,
        max_latency_ms: float = float("inf"),
        max_cost: float = float("inf"),
    ) -> Optional[ModelProfile]:
        """获取最佳模型（按质量评分）."""
        candidates = [
            m
            for m in self.find_models_for_task(task_type)
            if m.avg_latency_ms <= max_latency_ms and m.cost_per_1k_tokens <= max_cost
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda m: m.quality_scores.get(task_type, 0.0))

    def find_tool_calling_models(self) -> list[ModelProfile]:
        """查找支持 tool-calling 的模型."""
        return [m for m in self._models.values() if m.supports_tool_calling]

    def get_statistics(self) -> dict:
        """获取统计信息."""
        return {
            "total_models": len(self._models),
            "by_type": self._count_by_field("model_type"),
            "tool_calling_capable": len(self.find_tool_calling_models()),
        }

    def _count_by_field(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self._models.values():
            val = getattr(m, field, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts


def create_default_model_registry() -> ModelRegistry:
    """创建默认模型注册表."""
    registry = ModelRegistry()

    models = [
        ModelProfile(
            id="lightweight_sensing",
            name="轻量感知模型",
            model_type="lightweight",
            parameter_size="1B",
            supported_tasks=["sensing", "audio"],
            avg_latency_ms=20,
            cost_per_1k_tokens=0.001,
            quality_scores={"sensing": 0.7, "audio": 0.65},
        ),
        ModelProfile(
            id="vision_model",
            name="视觉理解模型",
            model_type="vision",
            parameter_size="3B",
            supported_tasks=["vision", "security_monitoring"],
            avg_latency_ms=80,
            cost_per_1k_tokens=0.005,
            quality_scores={"vision": 0.88, "security_monitoring": 0.82},
        ),
        ModelProfile(
            id="rag_model",
            name="RAG 检索模型",
            model_type="rag",
            parameter_size="7B",
            supported_tasks=["rag_retrieval", "context_aware_decision"],
            avg_latency_ms=150,
            cost_per_1k_tokens=0.003,
            quality_scores={"rag_retrieval": 0.85, "context_aware_decision": 0.8},
        ),
        ModelProfile(
            id="cloud_llm",
            name="云端大模型",
            model_type="llm",
            parameter_size="70B",
            supported_tasks=[
                "reasoning",
                "planning",
                "tool_calling",
                "emergency_response",
                "predictive_maintenance",
            ],
            avg_latency_ms=400,
            cost_per_1k_tokens=0.02,
            quality_scores={
                "reasoning": 0.95,
                "planning": 0.92,
                "tool_calling": 0.88,
            },
            supports_tool_calling=True,
        ),
    ]

    for m in models:
        registry.register(m)
    return registry
