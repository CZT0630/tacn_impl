"""任务 API — 处理请求 + 执行任务."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 内存存储: task_id → (plan, request_text)
_plans: dict[str, Any] = {}


class ProcessRequest(BaseModel):
    request: str
    deadline_ms: float = 30000


class ExecuteRequest(BaseModel):
    task_id: str


def get_system():
    """获取全局 TACNSystem 实例 (延迟导入避免循环)."""
    from backend.api.main import tacn_system
    return tacn_system


@router.post("/process")
async def process_request(body: ProcessRequest):
    """意图解析 + 子任务分解 + 路由 → 返回执行计划."""
    system = get_system()
    if system is None:
        raise HTTPException(500, "TACNSystem 未初始化")

    plan = await system.process_request(body.request, body.deadline_ms)
    task_id = str(uuid.uuid4())[:8]

    # 存储计划供后续执行
    _plans[task_id] = plan

    # 序列化为前端期望的格式
    return {
        "task_id": task_id,
        "intent": {
            "text": plan.intent.text,
            "type": plan.intent.intent_type.value,
            "privacy_level": plan.intent.privacy_level.value,
            "requires_collaboration": plan.intent.requires_collaboration,
            "deadline_ms": plan.intent.deadline_ms,
        },
        "subtask_graph": {
            "subtasks": [
                {
                    "id": st.id,
                    "name": st.name,
                    "description": st.description,
                    "priority": st.priority,
                    "capabilities": [c.capability_type.value for c in st.required_capabilities],
                    "tools": st.required_tools,
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
        "parallel_groups": plan.parallel_groups,
        "estimated_total_latency_ms": plan.estimated_total_latency_ms,
        "estimated_total_cost": plan.estimated_total_cost,
        "critical_path": plan.critical_path,
        "metadata": plan.metadata,
    }


@router.post("/execute")
async def execute_task(body: ExecuteRequest):
    """执行已规划的任务."""
    system = get_system()
    if system is None:
        raise HTTPException(500, "TACNSystem 未初始化")

    plan = _plans.get(body.task_id)
    if plan is None:
        raise HTTPException(404, f"任务 {body.task_id} 不存在，请先调用 /process")

    result = await system.execute_plan(plan)

    # 清理已执行的计划
    _plans.pop(body.task_id, None)

    return {
        "task_id": body.task_id,
        "status": result.status.value,
        "success": result.success,
        "actual_latency_ms": result.actual_latency_ms,
        "actual_cost": result.actual_cost,
        "subtask_results": {
            k: v for k, v in result.subtask_results.items()
            if isinstance(v, dict)
        },
        "output": result.output,
        "error": result.error,
    }
