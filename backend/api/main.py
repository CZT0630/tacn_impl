"""TACN FastAPI 入口.

启动: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import agents, experiments, tasks

app = FastAPI(
    title="TACN - Terminal Agent Computing Network",
    description="终端智能体算力网络",
    version="0.2.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])

# 静态文件 (前端)
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# ============================================================================
# 全局 TACNSystem 实例 — 启动时初始化
# ============================================================================

tacn_system = None


@app.on_event("startup")
async def startup():
    """启动时初始化 TACNSystem."""
    global tacn_system

    from backend.llm.config import LLMConfig
    from backend.orchestration.tacn_system import TACNSystem
    from backend.registry.agent_registry import create_default_registry
    from backend.registry.model_registry import create_default_model_registry
    from backend.registry.tool_registry import create_default_tool_registry
    from backend.registry.context_registry import create_default_context_registry
    from backend.infrastructure.network import NetworkModel

    llm_config = LLMConfig()

    tacn_system = TACNSystem(
        registry=create_default_registry(),
        llm_config=llm_config,
        model_registry=create_default_model_registry(),
        tool_registry=create_default_tool_registry(),
        context_registry=create_default_context_registry(),
        network_model=NetworkModel(),
    )

    agent_count = len(tacn_system.registry.get_all_agents())
    llm_status = "真实 LLM" if llm_config.api_key else "Mock"
    print(f"[TACN] 启动完成: {agent_count} 个 Agent, LLM={llm_status}")
