"""数据 API — 外部数据注入与查询.

传感器、摄像头、告警系统等外部数据源通过此 API 向 DataPool 灌入数据，
Agent 工具从 DataPool 读取最新值。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.datapool import DataPool

router = APIRouter()


# ============================================================================
# 请求模型
# ============================================================================


class PushRequest(BaseModel):
    """单条数据推送."""
    source: str = Field(..., description="数据源标识，如 sensor_001")
    type: str = Field(..., description="数据类型，如 temperature / smoke / image")
    value: Any = Field(..., description="数据值")
    ts: float | None = Field(None, description="时间戳，默认当前时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class BatchPushRequest(BaseModel):
    """批量数据推送."""
    items: list[PushRequest]


# ============================================================================
# 端点
# ============================================================================


@router.post("/push")
async def push_data(body: PushRequest):
    """推送单条数据到数据池.

    示例:
        POST /api/data/push
        {"source": "sensor_001", "type": "temperature", "value": 42.5}
    """
    pool = DataPool.get_instance()
    dp = pool.push(
        source=body.source,
        data_type=body.type,
        value=body.value,
        ts=body.ts,
        metadata=body.metadata,
    )
    return {
        "ok": True,
        "key": f"{dp.source}:{dp.type}",
        "ts": dp.ts,
    }


@router.post("/push/batch")
async def push_batch(body: BatchPushRequest):
    """批量推送数据.

    示例:
        POST /api/data/push/batch
        {"items": [
            {"source": "sensor_001", "type": "temperature", "value": 42.5},
            {"source": "sensor_001", "type": "smoke", "value": 0.12}
        ]}
    """
    pool = DataPool.get_instance()
    count = pool.push_batch([item.model_dump() for item in body.items])
    return {"ok": True, "pushed": count}


@router.get("/latest")
async def get_latest(
    source: str = Query(..., description="数据源"),
    type: str = Query(..., description="数据类型"),
):
    """获取指定源+类型的最新数据.

    示例:
        GET /api/data/latest?source=sensor_001&type=temperature
    """
    pool = DataPool.get_instance()
    dp = pool.get_latest(source, type)
    if dp is None:
        raise HTTPException(404, f"无数据: {source}:{type}")
    return {
        "source": dp.source,
        "type": dp.type,
        "value": dp.value,
        "ts": dp.ts,
        "metadata": dp.metadata,
    }


@router.get("/history")
async def get_history(
    source: str = Query(..., description="数据源"),
    type: str = Query(..., description="数据类型"),
    limit: int = Query(10, ge=1, le=200, description="最大返回条数"),
):
    """获取历史数据.

    示例:
        GET /api/data/history?source=sensor_001&type=temperature&limit=20
    """
    pool = DataPool.get_instance()
    points = pool.get_history(source, type, limit=limit)
    return {
        "source": source,
        "type": type,
        "count": len(points),
        "points": [
            {"value": p.value, "ts": p.ts, "metadata": p.metadata}
            for p in points
        ],
    }


@router.get("/snapshot")
async def get_snapshot():
    """获取所有源的最新数据快照.

    示例:
        GET /api/data/snapshot
    """
    pool = DataPool.get_instance()
    return {
        "data": pool.get_all_latest(),
        "statistics": pool.get_statistics(),
    }


@router.get("/sources")
async def list_sources():
    """列出所有数据源.

    示例:
        GET /api/data/sources
    """
    pool = DataPool.get_instance()
    sources = pool.list_sources()
    result = {}
    for src in sources:
        result[src] = pool.list_types(src)
    return {"sources": result}


@router.delete("/clear")
async def clear_data(
    source: str | None = Query(None, description="数据源，为空则清空全部"),
    type: str | None = Query(None, description="数据类型"),
):
    """清空数据池.

    示例:
        DELETE /api/data/clear?source=sensor_001
        DELETE /api/data/clear  (清空全部)
    """
    pool = DataPool.get_instance()
    pool.clear(source=source, data_type=type)
    return {"ok": True, "cleared": True}
