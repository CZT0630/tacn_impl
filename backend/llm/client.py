"""LLM 客户端抽象与实现.

参考 deer-flow 的类型化工厂模式:
- LLMClient: 抽象基类，定义统一接口
- OpenAIClient: OpenAI/Azure 兼容实现，支持 tool-calling
- MockLLMClient: 无 LLM 时的模拟实现
- create_llm_client: 工厂函数
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.llm.config import LLMConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class ToolCall:
    """Tool-calling 调用."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 响应."""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    raw: Any = None


# ============================================================================
# 抽象基类
# ============================================================================


class LLMClient(ABC):
    """LLM 客户端抽象基类."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """调用 LLM.

        Args:
            messages: 消息列表 [{"role": ..., "content": ...}]
            tools: 工具定义列表 (可选，用于 tool-calling)
            tool_choice: 工具选择策略 (可选)
            **kwargs: 额外参数

        Returns:
            LLMResponse 对象
        """


# ============================================================================
# OpenAI 实现
# ============================================================================


class OpenAIClient(LLMClient):
    """OpenAI / Azure 兼容 LLM 客户端.

    支持:
    - function calling / tool-calling
    - 指数退避重试
    - 自定义 base_url (兼容 DeepSeek、Ollama 等)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "需要安装 openai 包: pip install openai>=1.0"
            )

        client_kwargs: dict[str, Any] = {
            "api_key": api_key,
            "max_retries": max_retries,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """调用 OpenAI API."""
        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            call_kwargs["tools"] = tools
        if tool_choice:
            call_kwargs["tool_choice"] = tool_choice

        call_kwargs.update(kwargs)

        response = await self._client.chat.completions.create(**call_kwargs)
        choice = response.choices[0]

        # 解析 tool-calling
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = []
            import json

            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            raw=response,
        )


# ============================================================================
# Mock 实现
# ============================================================================


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端.

    无真实 API 调用，用于开发和测试。
    tool-calling 参数会被忽略，始终返回文本内容。
    """

    def __init__(self, response: str = ""):
        self._response = response

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """返回模拟响应."""
        return LLMResponse(content=self._response, tool_calls=None)


# ============================================================================
# 工厂函数
# ============================================================================


def create_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """根据配置创建 LLM 客户端.

    Args:
        config: LLM 配置。为 None 时返回 MockLLMClient。

    Returns:
        LLMClient 实例
    """
    if config is None or config.provider == "mock":
        return MockLLMClient()

    if config.provider == "openai":
        if not config.api_key:
            logger.warning("TACN_LLM_API_KEY 未设置，回退到 MockLLMClient")
            return MockLLMClient()
        return OpenAIClient(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            max_retries=config.max_retries,
            timeout=config.timeout,
        )

    logger.warning(f"未知的 LLM provider: {config.provider}，回退到 MockLLMClient")
    return MockLLMClient()
