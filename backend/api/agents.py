"""智能体 API — 查询智能体列表和统计."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


def get_system():
    from backend.api.main import tacn_system
    return tacn_system


@router.get("")
async def get_agents():
    """获取所有智能体信息."""
    system = get_system()
    if system is None:
        raise HTTPException(500, "TACNSystem 未初始化")

    registry = system.registry
    stats = system.agent_manager.get_agent_stats()

    agents = []
    for profile in registry.get_all_agents():
        agent_stats = stats.get(profile.id, {})
        agents.append({
            "id": profile.id,
            "name": profile.name,
            "location": profile.location.value,
            "description": profile.description,
            "capabilities": [
                {"type": c.capability_type.value, "quality": c.quality}
                for c in profile.capabilities
            ],
            "tools": agent_stats.get("tools", []),
            "current_load": profile.current_load,
            "max_concurrent_tasks": profile.max_concurrent_tasks,
            "avg_latency_ms": profile.avg_latency_ms,
            "cost_per_invocation": profile.cost_per_invocation,
            "privacy_level": profile.privacy_level.value,
            "reliability_score": profile.reliability_score,
        })

    statistics = registry.get_statistics()

    return {
        "agents": agents,
        "statistics": statistics,
    }
