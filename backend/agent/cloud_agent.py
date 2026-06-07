"""Cloud Agent — 云端智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from backend.agent.llm_agent import HookRegistry, LLMAgent, SkillLoader
from backend.agent.tools import ToolRegistry
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus
    from backend.llm.client import LLMClient


CLOUD_SYSTEM_PROMPT = """你是 {name}，部署在云端的 AI 智能体。

## 你的特点
- 最强的推理能力，可处理复杂多步任务
- 可访问全局知识库和互联网
- 可控制建筑设备（消防、门禁、通风等）
- 延迟较高（200-500ms），成本最高

## 工作方式
1. 收集来自终端和边缘的数据
2. 使用全局知识库和网络搜索补充信息
3. 进行深度分析和推理
4. 制定决策方案并控制执行设备
5. 必要时发送告警通知

请综合使用多个工具，给出完整的分析和决策方案。"""


class CloudAgent(LLMAgent):
    """云端智能体 — 全量工具 + 复杂推理."""

    COST_MULTIPLIER = 1.5

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClient | None = None,
        message_bus: Optional[MessageBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
        hooks: Optional[HookRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        system_prompt = CLOUD_SYSTEM_PROMPT.format(name=profile.name)
        super().__init__(profile, llm_client, message_bus, tool_registry=tool_registry, system_prompt=system_prompt, hooks=hooks, skill_loader=skill_loader)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        result = await super().execute(subtask, context)
        result.cost = result.cost * self.COST_MULTIPLIER
        result.metadata["agent_type"] = "cloud"
        return result
