"""TACN核心数据模型."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# 枚举类型
# ============================================================================

class IntentType(str, Enum):
    """意图类型."""
    EMERGENCY_RESPONSE = "emergency_response"
    ROBOT_INSPECTION = "robot_inspection"
    SECURITY_MONITORING = "security_monitoring"
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    MEETING_ASSISTANT = "meeting_assistant"


class CapabilityType(str, Enum):
    """能力类型."""
    SENSING = "sensing"
    VISION = "vision"
    AUDIO = "audio"
    REASONING = "reasoning"
    PLANNING = "planning"
    TOOL_CALLING = "tool_calling"
    RAG_RETRIEVAL = "rag_retrieval"
    NOTIFICATION = "notification"
    CONTROL = "control"
    COMPUTATION = "computation"
    COMMUNICATION = "communication"


class Location(str, Enum):
    """执行位置."""
    TERMINAL = "terminal"
    PEER = "peer"
    EDGE = "edge"
    CLOUD = "cloud"


class TaskStatus(str, Enum):
    """任务状态."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class PrivacyLevel(str, Enum):
    """隐私级别."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# ============================================================================
# 核心模型
# ============================================================================

class CapabilityRequirement(BaseModel):
    """能力需求."""
    capability_type: CapabilityType
    min_quality: float = Field(0.5, ge=0.0, le=1.0)


class Intent(BaseModel):
    """解析后的用户意图."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    intent_type: IntentType
    required_capabilities: list[CapabilityRequirement] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    deadline_ms: float = Field(30000.0, description="任务截止时间(毫秒)")
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    requires_collaboration: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class SubTask(BaseModel):
    """子任务."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    required_capabilities: list[CapabilityRequirement] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    estimated_computation: float = Field(100.0, description="预估计算量")
    estimated_data_size_kb: float = Field(50.0, description="预估数据量(KB)")
    priority: int = Field(5, ge=0, le=10)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubTaskEdge(BaseModel):
    """子任务依赖边."""
    source_id: str
    target_id: str
    dependency_type: str = "data"


class SubTaskGraph(BaseModel):
    """子任务依赖图(DAG)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent_id: str
    subtasks: list[SubTask] = Field(default_factory=list)
    edges: list[SubTaskEdge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def get_subtask(self, subtask_id: str) -> Optional[SubTask]:
        """根据ID获取子任务."""
        for st in self.subtasks:
            if st.id == subtask_id:
                return st
        return None

    def get_predecessors(self, subtask_id: str) -> list[str]:
        """获取前驱子任务ID."""
        return [e.source_id for e in self.edges if e.target_id == subtask_id]

    def get_successors(self, subtask_id: str) -> list[str]:
        """获取后继子任务ID."""
        return [e.target_id for e in self.edges if e.source_id == subtask_id]


class AgentCapability(BaseModel):
    """智能体能力."""
    capability_type: CapabilityType
    quality: float = Field(0.5, ge=0.0, le=1.0, description="能力质量")
    latency_ms: float = Field(0.0, ge=0.0, description="平均延迟(毫秒)")
    cost_per_invocation: float = Field(0.0, ge=0.0, description="每次调用成本")


class AgentProfile(BaseModel):
    """智能体配置."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: Location
    description: str = ""
    capabilities: list[AgentCapability] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    context_access: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = Field(1, ge=1)
    current_load: float = Field(0.0, ge=0.0, le=1.0)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    avg_latency_ms: float = Field(100.0, ge=0.0)
    cost_per_invocation: float = Field(0.01, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ---- 模型能力 ----
    supported_models: list[str] = Field(default_factory=list)
    default_model: str = ""

    # ---- 上下文能力 ----
    context_sources: list[str] = Field(default_factory=list)
    context_capacity_kb: float = 0.0

    # ---- 可靠性指标 (由反馈回路更新) ----
    reliability_score: float = Field(1.0, ge=0.0, le=1.0)
    observed_latency_ms: float = 0.0
    tool_success_rate: float = Field(1.0, ge=0.0, le=1.0)
    context_hit_rate: float = Field(0.0, ge=0.0, le=1.0)
    routing_score: float = Field(0.5, ge=0.0, le=1.0)

    def has_capability(self, cap_type: CapabilityType) -> bool:
        """检查是否具有某项能力."""
        return any(c.capability_type == cap_type for c in self.capabilities)

    def get_capability(self, cap_type: CapabilityType) -> Optional[AgentCapability]:
        """获取指定能力."""
        for c in self.capabilities:
            if c.capability_type == cap_type:
                return c
        return None

    def is_available(self) -> bool:
        """检查是否可用."""
        return self.current_load < 1.0

    def get_available_capacity(self) -> float:
        """获取可用容量."""
        return max(0.0, 1.0 - self.current_load)


class AgentMatchResult(BaseModel):
    """智能体匹配结果."""
    subtask_id: str
    agent_id: str
    score: float = Field(0.0, ge=0.0, le=1.0)
    capability_coverage: float = Field(0.0, ge=0.0, le=1.0)
    estimated_latency_ms: float = 0.0
    estimated_cost: float = 0.0
    privacy_satisfied: bool = True
    breakdown: dict[str, float] = Field(default_factory=dict)


class AgentAssignment(BaseModel):
    """子任务分配."""
    subtask_id: str
    agent_id: str
    location: Location
    estimated_start_ms: float = 0.0
    estimated_duration_ms: float = 0.0
    estimated_cost: float = 0.0
    priority: int = 0


class ExecutionPlan(BaseModel):
    """执行计划."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    intent: Intent
    subtask_graph: SubTaskGraph
    assignments: list[AgentAssignment] = Field(default_factory=list)
    estimated_total_latency_ms: float = 0.0
    estimated_total_cost: float = 0.0
    critical_path: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class SubTaskResult(BaseModel):
    """单个子任务执行结果."""
    subtask_id: str
    agent_id: str
    location: Location
    success: bool
    output: Any = None
    latency_ms: float = 0.0
    cost: float = 0.0
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """任务执行结果."""
    task_id: str
    plan_id: str
    status: TaskStatus
    actual_latency_ms: float = 0.0
    actual_cost: float = 0.0
    success: bool = False
    output: Optional[Any] = None
    error: Optional[str] = None
    subtask_results: dict[str, Any] = Field(default_factory=dict)
    agent_utilization: dict[str, float] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
