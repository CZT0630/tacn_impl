"""LLM 输出的 Pydantic 验证模型.

参考 deer-flow 的 Plan.model_validate 模式，用 Pydantic 做结构化验证。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
    """意图解析的结构化输出."""

    intent_type: str = "meeting_assistant"
    capabilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    privacy_level: str = "internal"
    deadline_ms: float = 30000.0
    context_needs: list[str] = Field(default_factory=list)
    requires_collaboration: bool = False


class SubTaskOutput(BaseModel):
    """单个子任务的结构化输出."""

    name: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    priority: int = Field(5, ge=1, le=10)
    estimated_computation: float = Field(100.0, gt=0)
    estimated_data_size_kb: float = Field(50.0, gt=0)


class SubTaskGraphOutput(BaseModel):
    """子任务图的结构化输出."""

    subtasks: list[SubTaskOutput] = Field(default_factory=list)
    dependencies: list[list[str]] = Field(default_factory=list)
