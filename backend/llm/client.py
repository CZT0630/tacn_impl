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
    当传入 tools 时，模拟 tool-calling 行为：
    - 第一次调用：调用第一个可用工具
    - 后续调用：返回基于工具结果的总结
    """

    def __init__(self, response: str = ""):
        self._response = response
        self._call_count = 0

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """返回模拟响应，支持 tool-calling 模拟."""
        # 无工具或已有工具结果时，返回文本
        has_tool_results = any(m.get("role") == "tool" for m in messages)

        if tools and not has_tool_results:
            # 模拟 LLM 决定调用第一个工具
            tool = tools[0]
            func = tool["function"]
            # 根据参数 schema 构造合理的 mock 参数
            mock_args = self._mock_arguments(func.get("parameters", {}))
            self._call_count += 1
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id=f"mock_call_{self._call_count}",
                        name=func["name"],
                        arguments=mock_args,
                    )
                ],
            )

        # 有工具结果或无工具时，返回文本
        content = self._response or "[Mock] 任务已完成"
        return LLMResponse(content=content, tool_calls=None)

    def _mock_arguments(self, schema: dict) -> dict:
        """根据 JSON Schema 构造 mock 参数."""
        args = {}
        props = schema.get("properties", {})
        for key, prop in props.items():
            prop_type = prop.get("type", "string")
            if prop.get("enum"):
                args[key] = prop["enum"][0]
            elif prop_type == "string":
                args[key] = prop.get("description", key)
            elif prop_type == "integer":
                args[key] = prop.get("default", 1)
            elif prop_type == "number":
                args[key] = prop.get("default", 1.0)
            elif prop_type == "boolean":
                args[key] = True
            elif prop_type == "array":
                args[key] = []
            elif prop_type == "object":
                args[key] = {}
        return args


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
