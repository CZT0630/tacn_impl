"""Edge Agent - 边缘智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.agent.llm_agent import LLMAgent
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class EdgeAgent(LLMAgent):
    """边缘智能体.

    部署在边缘服务器上.
    特点: 比终端强算力、比云端近、GPU加速、协调多终端.
    """

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(profile, llm_client, message_bus)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - 边缘版本."""
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "edge"
        return result
