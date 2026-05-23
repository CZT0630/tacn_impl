"""LLM Agent - 基于大语言模型的智能体基类."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from backend.agent.base import BaseAgent
from backend.core.models import (
    AgentProfile,
    SubTask,
    SubTaskResult,
)

if TYPE_CHECKING:
    from backend.agent.message import MessageBus


class LLMAgent(BaseAgent):
    """基于LLM的智能体.

    execute() 内部通过 LLM 完成子任务.
    LLM client 留接口，后续接入真实 LLM 时只需传入 client.
    """

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(profile, message_bus)
        self.llm_client = llm_client

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 - LLM版本.

        1. 构建 prompt
        2. 调用 LLM (或 mock)
        3. 返回 SubTaskResult
        """
        import time
        start = time.time()

        try:
            prompt = self._build_prompt(subtask, context)
            output = await self._call_llm(prompt)
            latency_ms = (time.time() - start) * 1000

            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=self.id,
                location=self.location,
                success=True,
                output=output,
                latency_ms=latency_ms,
                cost=self.profile.cost_per_invocation,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=self.id,
                location=self.location,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def _build_prompt(self, subtask: SubTask, context: dict | None) -> str:
        """构建LLM提示词."""
        caps = [c.capability_type.value for c in subtask.required_capabilities]
        tools = subtask.required_tools or []

        prompt = f"""你是一个部署在{self.location.value}层的AI智能体。
你的名称: {self.name}
你的能力: {', '.join(caps)}
你的可用工具: {', '.join(tools) if tools else '无'}

请执行以下子任务:
名称: {subtask.name}
描述: {subtask.description}
优先级: {subtask.priority}

请直接给出执行结果。"""

        if context:
            prompt += f"\n\n上下文信息: {context}"

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM.

        如果有真实LLM client则调用，否则返回mock结果.
        """
        if self.llm_client:
            try:
                messages = [{"role": "user", "content": prompt}]
                return await self.llm_client.chat(messages)
            except Exception as e:
                return f"LLM调用失败: {e}"

        # Mock结果 - 后续替换为真实LLM
        return f"[Mock] {self.name} 已完成子任务处理"
