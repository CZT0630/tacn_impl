"""Edge Agent — 边缘智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from backend.agent.llm_agent import HookRegistry, LLMAgent, SkillLoader
from backend.agent.tools import ToolRegistry
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus
    from backend.llm.client import LLMClient


EDGE_SYSTEM_PROMPT = """你是 {name}，部署在边缘服务器上的 AI 智能体。

## 你的特点
- 算力介于终端和云端之间，有 GPU 加速能力
- 可访问区域知识库（维护记录、本地文档）
- 可协调多个终端设备
- 延迟适中（50-200ms）

## 工作方式
1. 先用传感器/摄像头采集数据
2. 如果涉及知识检索（维护记录、应急预案等），使用知识库工具
3. 使用数据分析工具进行推理
4. 必要时发送告警通知

请综合使用多个工具完成任务。"""


class EdgeAgent(LLMAgent):
    """边缘智能体 — 区域知识库 + GPU 推理 + 告警."""

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClient | None = None,
        message_bus: Optional[MessageBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
        hooks: Optional[HookRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        system_prompt = EDGE_SYSTEM_PROMPT.format(name=profile.name)
        super().__init__(profile, llm_client, message_bus, tool_registry=tool_registry, system_prompt=system_prompt, hooks=hooks, skill_loader=skill_loader)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "edge"
        return result
