"""Terminal Agent — 终端智能体.

部署在终端设备(手机/传感器/摄像头)上.
特有行为: 隐私过滤、本地数据最小化处理、轻量推理.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from backend.agent.llm_agent import HookRegistry, LLMAgent, SkillLoader
from backend.agent.tools import ToolRegistry
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus
    from backend.llm.client import LLMClient


TERMINAL_SYSTEM_PROMPT = """你是 {name}，部署在终端设备（手机/传感器/摄像头）上的 AI 智能体。

## 你的特点
- 离数据源最近，延迟最低
- 资源受限，只能使用本地传感器和摄像头
- 隐私优先：绝不将敏感数据（用户ID、密码、生物特征等）传给云端

## 隐私约束
执行任务时，对上下文中的敏感字段（user_id, password, token, biometric, location_exact）进行脱敏处理后再使用。

## 可用工具
你可以使用传感器读取和摄像头采集工具。如果任务需要更强的推理或云端资源，说明你无法独立完成并建议上报给边缘或云端智能体。"""


class TerminalAgent(LLMAgent):
    """终端智能体 — 隐私过滤 + 本地工具."""

    SENSITIVE_KEYS = frozenset({
        "user_id", "location_exact", "biometric",
        "password", "token", "credit_card", "ssn",
    })

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClient | None = None,
        message_bus: Optional[MessageBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
        hooks: Optional[HookRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        system_prompt = TERMINAL_SYSTEM_PROMPT.format(name=profile.name)
        super().__init__(profile, llm_client, message_bus, tool_registry=tool_registry, system_prompt=system_prompt, hooks=hooks, skill_loader=skill_loader)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        filtered_context = self._filter_sensitive_data(context)
        result = await super().execute(subtask, filtered_context)
        result.metadata["agent_type"] = "terminal"
        result.metadata["privacy_filtered"] = context != filtered_context
        return result

    def _filter_sensitive_data(self, context: dict | None) -> dict | None:
        if not context:
            return context
        return {k: v for k, v in context.items() if k not in self.SENSITIVE_KEYS}
