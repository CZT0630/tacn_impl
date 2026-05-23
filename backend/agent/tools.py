"""Agent 工具 - 可被智能体调用的外部工具."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具基类."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """执行工具."""
        ...


class CameraTool(BaseTool):
    """摄像头工具."""

    def __init__(self):
        super().__init__("camera", "摄像头采集工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "image_captured": True,
                "resolution": "1920x1080",
                "objects_detected": ["person", "smoke"],
                "confidence": 0.87,
            },
        }


class SensorTool(BaseTool):
    """传感器工具."""

    def __init__(self):
        super().__init__("sensor", "传感器数据采集工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "temperature": 42.5,
                "humidity": 65.0,
                "smoke_level": 0.12,
                "timestamp": "2026-01-01T00:00:00",
            },
        }


class DocumentStoreTool(BaseTool):
    """文档检索工具."""

    def __init__(self):
        super().__init__("document_store", "文档存储检索工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        query = kwargs.get("query", "")
        return {
            "status": "success",
            "data": {
                "query": query,
                "results": [
                    {"title": "维护记录 #1024", "relevance": 0.92},
                    {"title": "安全规范 v3.1", "relevance": 0.85},
                ],
            },
        }


class NotificationTool(BaseTool):
    """通知工具."""

    def __init__(self):
        super().__init__("notification", "消息通知工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "message_sent": True,
                "recipients": kwargs.get("recipients", []),
                "channel": kwargs.get("channel", "sms"),
            },
        }


class LLMTool(BaseTool):
    """LLM 推理工具."""

    def __init__(self):
        super().__init__("llm", "大语言模型推理工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "response": "根据分析，建议启动应急响应流程。",
                "tokens_used": 256,
            },
        }


class VectorDatabaseTool(BaseTool):
    """向量数据库工具."""

    def __init__(self):
        super().__init__("vector_db", "向量数据库检索工具")

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "query": kwargs.get("query", ""),
                "matches": [
                    {"id": "doc_001", "score": 0.95},
                    {"id": "doc_002", "score": 0.88},
                ],
            },
        }


def create_default_tools() -> dict[str, BaseTool]:
    """创建默认工具集."""
    tools = [
        CameraTool(),
        SensorTool(),
        DocumentStoreTool(),
        NotificationTool(),
        LLMTool(),
        VectorDatabaseTool(),
    ]
    return {t.name: t for t in tools}
