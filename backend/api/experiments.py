"""实验 API — 对比实验 (stub)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

router = APIRouter()


@router.post("/run")
async def run_experiment(body: dict):
    """运行对比实验 (stub)."""
    experiment_id = str(uuid.uuid4())[:8]
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "message": "实验功能待实现，当前返回 stub 结果",
    }


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """获取实验结果 (stub)."""
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "results": {},
    }


@router.get("/{experiment_id}/chart")
async def get_experiment_chart(experiment_id: str):
    """获取实验图表数据 (stub)."""
    return {
        "experiment_id": experiment_id,
        "charts": {},
    }
