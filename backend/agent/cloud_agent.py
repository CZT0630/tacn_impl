"""Cloud Agent - 云端智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.agent.llm_agent import LLMAgent
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class CloudAgent(LLMAgent):
    """云端智能体.

    部署在云端.
    特点: 最强模型能力、全局上下文、跨区域知识、复杂推理.
    """

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(profile, llm_client, message_bus)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - 云端版本."""
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "cloud"
        return result
