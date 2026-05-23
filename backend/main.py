"""TACN后端入口 - FastAPI应用."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import agents, experiments, tasks

app = FastAPI(
    title="TACN - Terminal Agent Computing Network",
    description="终端智能体算力网络原型系统",
    version="0.1.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])


@app.get("/")
async def root():
    """根路径."""
    return {
        "name": "TACN - Terminal Agent Computing Network",
        "version": "0.1.0",
        "description": "终端智能体算力网络原型系统",
    }


@app.get("/api/health")
async def health():
    """健康检查."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
