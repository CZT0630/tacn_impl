"""智能体管理API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.registry.agent_registry import create_default_registry

router = APIRouter()

# 全局实例
registry = create_default_registry()


class UpdateLoadRequest(BaseModel):
    """更新负载请求."""
    load: float


@router.get("")
async def get_agents() -> dict:
    """获取所有智能体.

    Returns:
        智能体列表和统计信息
    """
    agents = registry.get_all_agents()
    stats = registry.get_statistics()

    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "location": a.location.value,
                "description": a.description,
                "capabilities": [
                    {
                        "type": c.capability_type.value,
                        "quality": c.quality,
                        "latency_ms": c.latency_ms,
                    }
                    for c in a.capabilities
                ],
                "tools": a.tools,
                "current_load": a.current_load,
                "max_concurrent_tasks": a.max_concurrent_tasks,
                "avg_latency_ms": a.avg_latency_ms,
                "cost_per_invocation": a.cost_per_invocation,
            }
            for a in agents
        ],
        "statistics": stats,
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    """获取单个智能体详情.

    Args:
        agent_id: 智能体ID

    Returns:
        智能体信息
    """
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent.id,
        "name": agent.name,
        "location": agent.location.value,
        "description": agent.description,
        "capabilities": [
            {
                "type": c.capability_type.value,
                "quality": c.quality,
                "latency_ms": c.latency_ms,
                "cost_per_invocation": c.cost_per_invocation,
            }
            for c in agent.capabilities
        ],
        "tools": agent.tools,
        "context_access": agent.context_access,
        "current_load": agent.current_load,
        "max_concurrent_tasks": agent.max_concurrent_tasks,
        "privacy_level": agent.privacy_level.value,
        "avg_latency_ms": agent.avg_latency_ms,
        "cost_per_invocation": agent.cost_per_invocation,
    }


@router.put("/{agent_id}/load")
async def update_load(agent_id: str, req: UpdateLoadRequest) -> dict:
    """更新智能体负载.

    Args:
        agent_id: 智能体ID
        req: 更新负载请求

    Returns:
        更新结果
    """
    success = registry.update_load(agent_id, req.load)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"success": True, "agent_id": agent_id, "new_load": req.load}


@router.get("/stats/summary")
async def get_stats() -> dict:
    """获取统计摘要.

    Returns:
        统计信息
    """
    return registry.get_statistics()
