"""LLM 配置."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM 客户端配置.

    支持从环境变量读取:
    - TACN_LLM_PROVIDER: 提供商 (openai | mock)
    - TACN_LLM_MODEL: 模型名称
    - TACN_LLM_API_KEY: API 密钥
    - TACN_LLM_BASE_URL: 自定义 API 地址
    """

    provider: str = field(
        default_factory=lambda: os.getenv("TACN_LLM_PROVIDER", "mock")
    )
    model: str = field(
        default_factory=lambda: os.getenv("TACN_LLM_MODEL", "gpt-4o")
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("TACN_LLM_API_KEY", "")
    )
    base_url: str | None = field(
        default_factory=lambda: os.getenv("TACN_LLM_BASE_URL")
    )
    max_retries: int = 3
    timeout: float = 30.0
