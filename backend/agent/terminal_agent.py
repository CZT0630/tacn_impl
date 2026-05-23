"""Terminal Agent - 终端智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.agent.llm_agent import LLMAgent
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class TerminalAgent(LLMAgent):
    """终端智能体.

    部署在终端设备(手机/传感器/摄像头)上.
    特点: 离数据源近、低延迟、隐私友好、资源受限.
    """

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(profile, llm_client, message_bus)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - 终端版本."""
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "terminal"
        return result
