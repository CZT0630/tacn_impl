"""Agent基类 - 统一所有Agent的接口."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from backend.core.models import (
    AgentCapability,
    AgentProfile,
    CapabilityType,
    Location,
    SubTask,
    SubTaskResult,
)

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class BaseAgent(ABC):
    """统一Agent接口.

    所有Agent(Terminal/Peer/Edge/Cloud)都继承此类.
    核心区别在于 agent_card 声明的能力不同.
    """

    def __init__(self, profile: AgentProfile, message_bus: Optional[MessageBus] = None):
        self.profile = profile
        self._communicator = None

        if message_bus is not None:
            from backend.agent.message import AgentCommunicator
            self._communicator = AgentCommunicator(profile.id, message_bus)

    @property
    def id(self) -> str:
        return self.profile.id

    @property
    def name(self) -> str:
        return self.profile.name

    @property
    def location(self) -> Location:
        return self.profile.location

    @property
    def communicator(self):
        return self._communicator

    def has_capability(self, cap_type: CapabilityType) -> bool:
        return self.profile.has_capability(cap_type)

    def get_capability(self, cap_type: CapabilityType) -> Optional[AgentCapability]:
        return self.profile.get_capability(cap_type)

    @abstractmethod
    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - 核心接口.

        Args:
            subtask: 要执行的子任务
            context: 执行上下文(可选)

        Returns:
            子任务执行结果
        """
        pass
