"""任务处理API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.models import ExecutionPlan, TaskResult
from backend.orchestration.tacn_system import TACNSystem
from backend.registry.agent_registry import create_default_registry

router = APIRouter()

# 全局实例
registry = create_default_registry()
tacn = TACNSystem(registry)

# 存储执行计划
plans_cache: dict[str, ExecutionPlan] = {}


class ProcessRequest(BaseModel):
    """处理请求."""
    request: str
    deadline_ms: Optional[float] = 30000


class ExecuteRequest(BaseModel):
    """执行请求."""
    task_id: str


@router.post("/process")
async def process_request(req: ProcessRequest) -> dict:
    """处理用户请求，返回执行计划."""
    try:
        plan = await tacn.process_request(req.request, req.deadline_ms)
        plans_cache[plan.task_id] = plan

        return {
            "task_id": plan.task_id,
            "intent": {
                "type": plan.intent.intent_type.value,
                "text": plan.intent.text,
                "deadline_ms": plan.intent.deadline_ms,
                "privacy_level": plan.intent.privacy_level.value,
            },
            "subtask_graph": {
                "num_subtasks": len(plan.subtask_graph.subtasks),
                "num_edges": len(plan.subtask_graph.edges),
                "subtasks": [
                    {
                        "id": st.id,
                        "name": st.name,
                        "description": st.description,
                        "priority": st.priority,
                        "estimated_computation": st.estimated_computation,
                        "required_capabilities": [
                            c.capability_type.value for c in st.required_capabilities
                        ],
                    }
                    for st in plan.subtask_graph.subtasks
                ],
                "edges": [
                    {"source": e.source_id, "target": e.target_id}
                    for e in plan.subtask_graph.edges
                ],
            },
            "assignments": [
                {
                    "subtask_id": a.subtask_id,
                    "agent_id": a.agent_id,
                    "location": a.location.value,
                    "estimated_duration_ms": a.estimated_duration_ms,
                    "estimated_cost": a.estimated_cost,
                }
                for a in plan.assignments
            ],
            "estimated_total_latency_ms": plan.estimated_total_latency_ms,
            "estimated_total_cost": plan.estimated_total_cost,
            "critical_path_length": len(plan.critical_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_task(req: ExecuteRequest) -> dict:
    """执行任务."""
    plan = plans_cache.get(req.task_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        result = await tacn.execute_plan(plan)

        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "success": result.success,
            "actual_latency_ms": result.actual_latency_ms,
            "actual_cost": result.actual_cost,
            "subtask_results": result.subtask_results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents() -> dict:
    """获取所有Agent信息."""
    agents = registry.get_all_agents()
    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "location": a.location.value,
                "capabilities": [
                    {"type": c.capability_type.value, "quality": c.quality}
                    for c in a.capabilities
                ],
                "tools": a.tools,
                "avg_latency_ms": a.avg_latency_ms,
                "privacy_level": a.privacy_level.value,
            }
            for a in agents
        ]
    }


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict:
    """获取任务详情."""
    plan = plans_cache.get(task_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": plan.task_id,
        "intent_type": plan.intent.intent_type.value,
        "text": plan.intent.text,
        "num_subtasks": len(plan.subtask_graph.subtasks),
        "estimated_latency_ms": plan.estimated_total_latency_ms,
        "estimated_cost": plan.estimated_total_cost,
    }
