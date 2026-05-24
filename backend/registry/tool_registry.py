"""工具注册表."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.core.models import CapabilityType, PrivacyLevel


class ToolProfile(BaseModel):
    """工具画像."""

    id: str
    name: str
    tool_type: str  # "api", "device_control", "data_source", "notification"
    description: str = ""
    input_schema: dict = Field(default_factory=dict)
    avg_latency_ms: float = 50.0
    success_rate: float = 0.95
    privacy_impact: PrivacyLevel = PrivacyLevel.INTERNAL
    required_permissions: list[str] = Field(default_factory=list)
    related_capabilities: list[CapabilityType] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ToolRegistry:
    """工具注册表.

    维护所有可用工具的画像，支持按能力/隐私影响查询.
    """

    def __init__(self):
        self._tools: dict[str, ToolProfile] = {}

    def register(self, tool: ToolProfile):
        """注册工具."""
        self._tools[tool.id] = tool

    def unregister(self, tool_id: str) -> bool:
        """注销工具."""
        return self._tools.pop(tool_id, None) is not None

    def get_tool(self, tool_id: str) -> Optional[ToolProfile]:
        """获取工具."""
        return self._tools.get(tool_id)

    def get_all_tools(self) -> list[ToolProfile]:
        """获取所有工具."""
        return list(self._tools.values())

    def find_tools_for_capability(self, cap_type: CapabilityType) -> list[ToolProfile]:
        """查找与指定能力相关的工具."""
        return [t for t in self._tools.values() if cap_type in t.related_capabilities]

    def find_tools_by_type(self, tool_type: str) -> list[ToolProfile]:
        """按类型查找工具."""
        return [t for t in self._tools.values() if t.tool_type == tool_type]

    def check_privacy_compatible(
        self, tool_id: str, max_privacy: PrivacyLevel
    ) -> bool:
        """检查工具的隐私影响是否在允许范围内."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        privacy_order = {
            PrivacyLevel.PUBLIC: 0,
            PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2,
            PrivacyLevel.RESTRICTED: 3,
        }
        return privacy_order.get(tool.privacy_impact, 0) <= privacy_order.get(
            max_privacy, 3
        )

    def get_statistics(self) -> dict:
        """获取统计信息."""
        return {
            "total_tools": len(self._tools),
            "by_type": self._count_by_field("tool_type"),
        }

    def _count_by_field(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in self._tools.values():
            val = getattr(t, field, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts


def create_default_tool_registry() -> ToolRegistry:
    """创建默认工具注册表."""
    registry = ToolRegistry()

    tools = [
        ToolProfile(
            id="camera",
            name="摄像头",
            tool_type="device_control",
            avg_latency_ms=30,
            related_capabilities=[CapabilityType.VISION],
        ),
        ToolProfile(
            id="temperature_sensor",
            name="温度传感器",
            tool_type="device_control",
            avg_latency_ms=5,
            related_capabilities=[CapabilityType.SENSING],
        ),
        ToolProfile(
            id="smoke_detector",
            name="烟雾探测器",
            tool_type="device_control",
            avg_latency_ms=3,
            related_capabilities=[CapabilityType.SENSING],
        ),
        ToolProfile(
            id="vector_database",
            name="向量数据库",
            tool_type="data_source",
            avg_latency_ms=80,
            related_capabilities=[CapabilityType.RAG_RETRIEVAL],
        ),
        ToolProfile(
            id="document_store",
            name="文档存储",
            tool_type="data_source",
            avg_latency_ms=100,
            related_capabilities=[CapabilityType.RAG_RETRIEVAL],
        ),
        ToolProfile(
            id="notification_service",
            name="通知服务",
            tool_type="api",
            avg_latency_ms=50,
            related_capabilities=[CapabilityType.NOTIFICATION],
        ),
        ToolProfile(
            id="work_order_system",
            name="工单系统",
            tool_type="api",
            avg_latency_ms=80,
            related_capabilities=[CapabilityType.TOOL_CALLING],
        ),
        ToolProfile(
            id="llm_api",
            name="LLM API",
            tool_type="api",
            avg_latency_ms=300,
            related_capabilities=[CapabilityType.REASONING],
        ),
    ]

    for t in tools:
        registry.register(t)
    return registry
