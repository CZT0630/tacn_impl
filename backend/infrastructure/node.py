"""节点资源状态模型."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.core.models import Location


class NodeStatus(BaseModel):
    """节点资源状态."""

    node_id: str
    location: Location
    cpu_usage: float = Field(0.0, ge=0.0, le=1.0)
    memory_usage: float = Field(0.0, ge=0.0, le=1.0)
    gpu_usage: float = Field(0.0, ge=0.0, le=1.0)
    queue_depth: int = 0
    energy_remaining: float = Field(1.0, ge=0.0, le=1.0)
    is_online: bool = True
