"""Peer Agent - 对等智能体."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.agent.llm_agent import LLMAgent
from backend.core.models import AgentProfile, SubTask, SubTaskResult

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class PeerAgent(LLMAgent):
    """对等智能体.

    部署在邻近终端之间，支持D2D协作.
    特点: 多终端数据融合、降低云端依赖.
    """

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(profile, llm_client, message_bus)

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - 对等版本."""
        result = await super().execute(subtask, context)
        result.metadata["agent_type"] = "peer"
        return result
