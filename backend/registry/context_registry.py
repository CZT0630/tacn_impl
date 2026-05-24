"""上下文注册表."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.core.models import Location, PrivacyLevel


class ContextSource(BaseModel):
    """上下文源."""

    id: str
    name: str
    context_type: str  # "user_profile", "environment", "device_state", "history", "knowledge_base"
    location: Location  # 数据所在位置
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    access_cost_ms: float = 10.0
    size_kb: float = 0.0
    description: str = ""
    metadata: dict = Field(default_factory=dict)


class ContextRegistry:
    """上下文注册表.

    维护所有可用上下文源，支持按类型/位置/隐私级别查询.
    """

    def __init__(self):
        self._sources: dict[str, ContextSource] = {}

    def register(self, source: ContextSource):
        """注册上下文源."""
        self._sources[source.id] = source

    def unregister(self, source_id: str) -> bool:
        """注销上下文源."""
        return self._sources.pop(source_id, None) is not None

    def get_context(self, context_id: str) -> Optional[ContextSource]:
        """获取上下文源."""
        return self._sources.get(context_id)

    def get_all_sources(self) -> list[ContextSource]:
        """获取所有上下文源."""
        return list(self._sources.values())

    def find_by_type(self, context_type: str) -> list[ContextSource]:
        """按类型查找."""
        return [s for s in self._sources.values() if s.context_type == context_type]

    def find_by_location(self, location: Location) -> list[ContextSource]:
        """按位置查找."""
        return [s for s in self._sources.values() if s.location == location]

    def find_for_task(
        self,
        required_context: list[str],
        max_privacy: PrivacyLevel = PrivacyLevel.RESTRICTED,
    ) -> list[ContextSource]:
        """查找任务所需的上下文源."""
        privacy_order = {
            PrivacyLevel.PUBLIC: 0,
            PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2,
            PrivacyLevel.RESTRICTED: 3,
        }
        max_level = privacy_order.get(max_privacy, 3)
        return [
            s
            for s in self._sources.values()
            if s.id in required_context
            and privacy_order.get(s.privacy_level, 0) <= max_level
        ]

    def get_statistics(self) -> dict:
        """获取统计信息."""
        return {
            "total_sources": len(self._sources),
            "by_type": self._count_by_field("context_type"),
            "by_location": self._count_by_location(),
        }

    def _count_by_field(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self._sources.values():
            val = getattr(s, field, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts

    def _count_by_location(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self._sources.values():
            counts[s.location.value] = counts.get(s.location.value, 0) + 1
        return counts


def create_default_context_registry() -> ContextRegistry:
    """创建默认上下文注册表."""
    registry = ContextRegistry()

    sources = [
        ContextSource(
            id="user_profile",
            name="用户画像",
            context_type="user_profile",
            location=Location.TERMINAL,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
        ),
        ContextSource(
            id="location_history",
            name="位置历史",
            context_type="history",
            location=Location.TERMINAL,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
        ),
        ContextSource(
            id="sensor_history",
            name="传感器历史",
            context_type="history",
            location=Location.EDGE,
            privacy_level=PrivacyLevel.INTERNAL,
        ),
        ContextSource(
            id="maintenance_records",
            name="维护记录",
            context_type="knowledge_base",
            location=Location.EDGE,
            privacy_level=PrivacyLevel.INTERNAL,
        ),
        ContextSource(
            id="local_knowledge_base",
            name="本地知识库",
            context_type="knowledge_base",
            location=Location.EDGE,
            privacy_level=PrivacyLevel.INTERNAL,
        ),
        ContextSource(
            id="global_knowledge_base",
            name="全局知识库",
            context_type="knowledge_base",
            location=Location.CLOUD,
            privacy_level=PrivacyLevel.INTERNAL,
        ),
        ContextSource(
            id="security_policies",
            name="安全策略",
            context_type="knowledge_base",
            location=Location.CLOUD,
            privacy_level=PrivacyLevel.INTERNAL,
        ),
        ContextSource(
            id="network_state",
            name="网络状态",
            context_type="environment",
            location=Location.EDGE,
            privacy_level=PrivacyLevel.PUBLIC,
        ),
    ]

    for s in sources:
        registry.register(s)
    return registry
