"""智能体注册表 - 管理所有智能体的能力信息."""

from __future__ import annotations

from typing import Optional

from backend.core.models import (
    AgentCapability,
    AgentProfile,
    CapabilityType,
    Location,
    PrivacyLevel,
)


class AgentRegistry:
    """智能体注册表.

    提供智能体注册、发现和查询功能.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._index_by_location: dict[Location, set[str]] = {
            loc: set() for loc in Location
        }
        self._index_by_capability: dict[CapabilityType, set[str]] = {
            cap: set() for cap in CapabilityType
        }

    def register(self, agent: AgentProfile) -> None:
        """注册智能体."""
        self._agents[agent.id] = agent
        self._index_by_location[agent.location].add(agent.id)
        for cap in agent.capabilities:
            self._index_by_capability[cap.capability_type].add(agent.id)

    def unregister(self, agent_id: str) -> bool:
        """注销智能体."""
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return False
        self._index_by_location[agent.location].discard(agent.id)
        for cap in agent.capabilities:
            self._index_by_capability[cap.capability_type].discard(agent.id)
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """获取智能体."""
        return self._agents.get(agent_id)

    def get_all_agents(self) -> list[AgentProfile]:
        """获取所有智能体."""
        return list(self._agents.values())

    def get_agents_by_location(self, location: Location) -> list[AgentProfile]:
        """按位置获取智能体."""
        agent_ids = self._index_by_location.get(location, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_by_capability(self, cap_type: CapabilityType) -> list[AgentProfile]:
        """按能力获取智能体."""
        agent_ids = self._index_by_capability.get(cap_type, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_available_agents(self) -> list[AgentProfile]:
        """获取可用智能体."""
        return [a for a in self._agents.values() if a.is_available()]

    def update_load(self, agent_id: str, load: float) -> bool:
        """更新智能体负载."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.current_load = max(0.0, min(1.0, load))
        return True

    def get_statistics(self) -> dict:
        """获取注册表统计信息."""
        stats = {
            "total_agents": len(self._agents),
            "by_location": {},
            "by_capability": {},
            "available_agents": len(self.get_available_agents()),
            "avg_load": 0.0,
        }

        for loc in Location:
            agents = self.get_agents_by_location(loc)
            stats["by_location"][loc.value] = len(agents)

        for cap in CapabilityType:
            agents = self.get_agents_by_capability(cap)
            stats["by_capability"][cap.value] = len(agents)

        if self._agents:
            total_load = sum(a.current_load for a in self._agents.values())
            stats["avg_load"] = total_load / len(self._agents)

        return stats

    def clear(self) -> None:
        """清空注册表."""
        self._agents.clear()
        self._index_by_location = {loc: set() for loc in Location}
        self._index_by_capability = {cap: set() for cap in CapabilityType}


def create_default_registry() -> AgentRegistry:
    """创建默认智能体注册表(用于测试)."""
    registry = AgentRegistry()

    # 终端智能体
    terminal_agents = [
        AgentProfile(
            name="phone_agent_001",
            location=Location.TERMINAL,
            description="智能手机智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.SENSING, quality=0.7, latency_ms=10),
                AgentCapability(capability_type=CapabilityType.VISION, quality=0.6, latency_ms=50),
                AgentCapability(capability_type=CapabilityType.AUDIO, quality=0.7, latency_ms=20),
            ],
            tools=["camera", "microphone", "gps"],
            context_access=["user_profile", "location_history"],
            max_concurrent_tasks=2,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            avg_latency_ms=30,
            supported_models=["lightweight_sensing", "vision_model"],
            default_model="lightweight_sensing",
            context_sources=["user_profile", "location_history"],
            context_capacity_kb=512,
        ),
        AgentProfile(
            name="camera_agent_001",
            location=Location.TERMINAL,
            description="智能摄像头智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.VISION, quality=0.85, latency_ms=30),
                AgentCapability(capability_type=CapabilityType.SENSING, quality=0.9, latency_ms=5),
            ],
            tools=["camera", "motion_detector"],
            context_access=["scene_history"],
            max_concurrent_tasks=1,
            privacy_level=PrivacyLevel.INTERNAL,
            avg_latency_ms=20,
            supported_models=["vision_model", "lightweight_sensing"],
            default_model="vision_model",
            context_sources=["sensor_history"],
            context_capacity_kb=256,
        ),
        AgentProfile(
            name="sensor_agent_001",
            location=Location.TERMINAL,
            description="IoT传感器智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.SENSING, quality=0.95, latency_ms=2),
            ],
            tools=["temperature_sensor", "smoke_detector", "humidity_sensor"],
            context_access=["sensor_history"],
            max_concurrent_tasks=3,
            privacy_level=PrivacyLevel.INTERNAL,
            avg_latency_ms=5,
            supported_models=["lightweight_sensing"],
            default_model="lightweight_sensing",
            context_sources=["sensor_history"],
            context_capacity_kb=128,
        ),
    ]

    # 对等智能体
    peer_agents = [
        AgentProfile(
            name="robot_agent_001",
            location=Location.PEER,
            description="移动巡检机器人智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.VISION, quality=0.8, latency_ms=40),
                AgentCapability(capability_type=CapabilityType.SENSING, quality=0.85, latency_ms=15),
                AgentCapability(capability_type=CapabilityType.CONTROL, quality=0.7, latency_ms=100),
                AgentCapability(capability_type=CapabilityType.COMMUNICATION, quality=0.9, latency_ms=20),
            ],
            tools=["lidar", "camera", "navigation_system"],
            context_access=["robot_state", "map_data"],
            max_concurrent_tasks=1,
            privacy_level=PrivacyLevel.INTERNAL,
            avg_latency_ms=50,
            supported_models=["vision_model", "lightweight_sensing"],
            default_model="vision_model",
            context_sources=["sensor_history", "maintenance_records"],
            context_capacity_kb=1024,
        ),
    ]

    # 边缘智能体
    edge_agents = [
        AgentProfile(
            name="edge_vision_agent",
            location=Location.EDGE,
            description="边缘视觉处理智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.VISION, quality=0.92, latency_ms=80),
                AgentCapability(capability_type=CapabilityType.REASONING, quality=0.7, latency_ms=200),
                AgentCapability(capability_type=CapabilityType.COMPUTATION, quality=0.85, latency_ms=50),
            ],
            tools=["gpu_cluster", "vision_models"],
            context_access=["video_feeds", "scene_database"],
            max_concurrent_tasks=5,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            avg_latency_ms=100,
            supported_models=["vision_model", "rag_model"],
            default_model="vision_model",
            context_sources=["sensor_history", "maintenance_records", "network_state"],
            context_capacity_kb=4096,
        ),
        AgentProfile(
            name="edge_rag_agent",
            location=Location.EDGE,
            description="边缘RAG检索智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.RAG_RETRIEVAL, quality=0.88, latency_ms=150),
                AgentCapability(capability_type=CapabilityType.REASONING, quality=0.75, latency_ms=300),
            ],
            tools=["vector_database", "document_store"],
            context_access=["local_knowledge_base", "maintenance_records"],
            max_concurrent_tasks=3,
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            avg_latency_ms=150,
            supported_models=["rag_model"],
            default_model="rag_model",
            context_sources=["local_knowledge_base", "maintenance_records"],
            context_capacity_kb=8192,
        ),
        AgentProfile(
            name="edge_orchestrator",
            location=Location.EDGE,
            description="边缘编排智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.PLANNING, quality=0.85, latency_ms=100),
                AgentCapability(capability_type=CapabilityType.TOOL_CALLING, quality=0.9, latency_ms=50),
                AgentCapability(capability_type=CapabilityType.COMMUNICATION, quality=0.95, latency_ms=30),
                AgentCapability(capability_type=CapabilityType.NOTIFICATION, quality=0.8, latency_ms=40),
            ],
            tools=["agent_registry", "task_scheduler", "notification_service"],
            context_access=["network_state", "agent_status"],
            max_concurrent_tasks=10,
            privacy_level=PrivacyLevel.INTERNAL,
            avg_latency_ms=50,
            supported_models=["cloud_llm", "rag_model"],
            default_model="rag_model",
            context_sources=["network_state"],
            context_capacity_kb=2048,
        ),
    ]

    # 云端智能体
    cloud_agents = [
        AgentProfile(
            name="cloud_llm_agent",
            location=Location.CLOUD,
            description="云端大模型智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.REASONING, quality=0.95, latency_ms=500),
                AgentCapability(capability_type=CapabilityType.PLANNING, quality=0.92, latency_ms=400),
                AgentCapability(capability_type=CapabilityType.RAG_RETRIEVAL, quality=0.9, latency_ms=300),
                AgentCapability(capability_type=CapabilityType.TOOL_CALLING, quality=0.88, latency_ms=200),
                AgentCapability(capability_type=CapabilityType.NOTIFICATION, quality=0.85, latency_ms=300),
            ],
            tools=["llm_api", "web_search", "code_executor", "notification_service"],
            context_access=["global_knowledge_base", "user_history"],
            max_concurrent_tasks=20,
            privacy_level=PrivacyLevel.RESTRICTED,
            cost_per_invocation=0.05,
            avg_latency_ms=400,
            supported_models=["cloud_llm", "rag_model", "vision_model"],
            default_model="cloud_llm",
            context_sources=["global_knowledge_base", "security_policies"],
            context_capacity_kb=32768,
        ),
        AgentProfile(
            name="cloud_security_agent",
            location=Location.CLOUD,
            description="云端安全分析智能体",
            capabilities=[
                AgentCapability(capability_type=CapabilityType.REASONING, quality=0.9, latency_ms=600),
                AgentCapability(capability_type=CapabilityType.TOOL_CALLING, quality=0.85, latency_ms=250),
            ],
            tools=["security_scanner", "compliance_checker"],
            context_access=["security_policies", "audit_logs"],
            max_concurrent_tasks=10,
            privacy_level=PrivacyLevel.RESTRICTED,
            cost_per_invocation=0.03,
            avg_latency_ms=500,
            supported_models=["cloud_llm"],
            default_model="cloud_llm",
            context_sources=["security_policies"],
            context_capacity_kb=16384,
        ),
    ]

    for agent in terminal_agents + peer_agents + edge_agents + cloud_agents:
        registry.register(agent)

    return registry
