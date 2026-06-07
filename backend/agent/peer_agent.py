"""Peer Agent — 对等智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from backend.agent.llm_agent import HookRegistry, LLMAgent, SkillLoader
from backend.agent.tools import ToolRegistry
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus
    from backend.llm.client import LLMClient


PEER_SYSTEM_PROMPT = """你是 {name}，部署在邻近终端之间的对等智能体。

## 你的特点
- 可与其他终端设备进行 D2D 直连通信
- 支持多终端数据融合和协同感知
- 降低对云端的依赖，适合本地协作场景

## 工作方式
1. 读取本地传感器数据
2. 通过 D2D 通信与邻近设备交换数据
3. 融合多设备数据进行分析
4. 给出协同感知结果

请利用 D2D 协作能力完成任务。"""


class PeerAgent(LLMAgent):
    """对等智能体 — D2D 通信 + 协同感知."""

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClient | None = None,
        message_bus: Optional[MessageBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
        hooks: Optional[HookRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        system_prompt = PEER_SYSTEM_PROMPT.format(name=profile.name)
        super().__init__(profile, llm_client, message_bus, tool_registry=tool_registry, system_prompt=system_prompt, hooks=hooks, skill_loader=skill_loader)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "peer"
        result.metadata["d2d_collaboration"] = True
        return result
