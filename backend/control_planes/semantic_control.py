"""语义与智能体控制面."""

from __future__ import annotations

from backend.core.models import AgentAssignment, Intent
from backend.registry.agent_registry import AgentRegistry
from backend.registry.context_registry import ContextRegistry
from backend.registry.model_registry import ModelRegistry
from backend.registry.tool_registry import ToolRegistry


class SemanticControlPlane:
    """语义与智能体控制面.

    职责: 用户意图解析、任务语义识别、子任务图生成、
    智能体能力发现、能力匹配、模型/工具/上下文选择、
    多智能体协作关系管理.

    回答: 用户真正想完成什么？该任务需要哪些能力？应由哪些智能体协同完成？
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        context_registry: ContextRegistry,
    ):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.context_registry = context_registry

    def discover_capabilities(self, intent: Intent) -> dict:
        """发现满足意图所需的能力."""
        available_agents = {}
        for cap_req in intent.required_capabilities:
            agents = self.agent_registry.get_agents_by_capability(
                cap_req.capability_type
            )
            available_agents[cap_req.capability_type.value] = [
                {
                    "id": a.id,
                    "name": a.name,
                    "location": a.location.value,
                    "quality": next(
                        (
                            c.quality
                            for c in a.capabilities
                            if c.capability_type == cap_req.capability_type
                        ),
                        0.0,
                    ),
                }
                for a in agents
            ]
        return available_agents

    def get_collaboration_topology(
        self, assignments: list[AgentAssignment]
    ) -> dict:
        """分析多智能体协作拓扑."""
        agents_used = set(a.agent_id for a in assignments)
        locations_used = set(a.location.value for a in assignments)
        return {
            "num_agents": len(agents_used),
            "num_locations": len(locations_used),
            "agents": list(agents_used),
            "locations": list(locations_used),
        }

    def get_available_models(self) -> list[dict]:
        """获取所有可用模型."""
        return [
            {"id": m.id, "name": m.name, "type": m.model_type}
            for m in self.model_registry.get_all_models()
        ]

    def get_available_tools(self) -> list[dict]:
        """获取所有可用工具."""
        return [
            {"id": t.id, "name": t.name, "type": t.tool_type}
            for t in self.tool_registry.get_all_tools()
        ]

    def get_available_contexts(self) -> list[dict]:
        """获取所有可用上下文源."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.context_type,
                "location": s.location.value,
            }
            for s in self.context_registry.get_all_sources()
        ]
