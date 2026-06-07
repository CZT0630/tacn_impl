"""Agent 工具系统 — 支持两种注册方式.

模式 1 (LCC dispatch map): 函数 + schema 声明，零 boilerplate
模式 2 (传统类): 继承 AgentTool ABC，适合复杂工具

两种模式可以混用，统一转为 OpenAI function schema 传给 LLM.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ============================================================================
# 模式 1: Dispatch Map — LCC 风格
# ============================================================================


@dataclass
class ToolDef:
    """工具定义 — 函数 + schema，零 boilerplate.

    用法:
        read_sensor = ToolDef(
            name="read_sensor",
            description="读取传感器数据",
            parameters={"type": "object", "properties": {...}, "required": [...]},
            handler=async lambda **kw: {...},
        )
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]  # async callable

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        return await self.handler(**kwargs)


# ============================================================================
# 模式 2: 类继承 — 传统方式，向后兼容
# ============================================================================


class AgentTool(ABC):
    """Agent 可调用的工具基类 (向后兼容)."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def parameters_schema(self) -> dict:
        """返回 OpenAI function 的 parameters JSON Schema."""

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema(),
            },
        }

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """执行工具，返回结果."""


# ============================================================================
# 工具注册表 — 统一管理
# ============================================================================


class ToolRegistry:
    """工具注册表 — 支持动态注册/查询/按 agent 分组.

    用法:
        registry = ToolRegistry()
        registry.register(ToolDef(...))           # 注册函数式工具
        registry.register(SomeAgentTool())        # 注册类式工具
        registry.register_group("terminal", ["read_sensor", "capture_image"])
        tools = registry.get_tools_for("terminal")
    """

    def __init__(self):
        self._tools: dict[str, ToolDef | AgentTool] = {}
        self._groups: dict[str, list[str]] = {}

    def register(self, tool: ToolDef | AgentTool) -> None:
        """注册工具 (函数式或类式)."""
        self._tools[tool.name] = tool

    def register_function(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
    ) -> ToolDef:
        """快捷注册函数式工具."""
        tool = ToolDef(name=name, description=description, parameters=parameters, handler=handler)
        self._tools[name] = tool
        return tool

    def register_group(self, group_name: str, tool_names: list[str]) -> None:
        """注册工具组 (如 terminal/edge/cloud)."""
        self._groups[group_name] = tool_names

    def get_tool(self, name: str) -> ToolDef | AgentTool | None:
        return self._tools.get(name)

    def get_tools_for(self, group_name: str) -> list[ToolDef | AgentTool]:
        """获取指定组的工具列表."""
        names = self._groups.get(group_name, [])
        return [self._tools[n] for n in names if n in self._tools]

    def get_all_tools(self) -> list[ToolDef | AgentTool]:
        return list(self._tools.values())

    def get_all_schemas(self) -> list[dict]:
        """获取所有工具的 OpenAI schema."""
        return [t.to_openai_tool() for t in self._tools.values()]

    def get_schemas_for(self, group_name: str) -> list[dict]:
        """获取指定组的 OpenAI schema."""
        return [t.to_openai_tool() for t in self.get_tools_for(group_name)]

    def get_handlers_map(self) -> dict[str, Callable]:
        """获取所有工具的 handler 映射 (dispatch map)."""
        return {name: t.execute for name, t in self._tools.items()}


# ============================================================================
# 内置工具实现 — IoT 场景
# ============================================================================


async def _read_sensor(sensor_type: str = "temperature", location: str = "未知位置") -> dict:
    """读取传感器数据."""
    mock_data = {
        "temperature": {"value": 42.5, "unit": "°C", "threshold": 60, "status": "warning"},
        "humidity": {"value": 65.0, "unit": "%", "threshold": 80, "status": "normal"},
        "smoke": {"value": 0.12, "unit": "ppm", "threshold": 0.05, "status": "ALERT"},
        "motion": {"detected": True, "confidence": 0.92, "zone": "A3"},
        "light": {"value": 350, "unit": "lux", "status": "normal"},
    }
    data = mock_data.get(sensor_type, {"value": 0, "status": "unknown"})
    return {"sensor_type": sensor_type, "location": location, "data": data}


async def _capture_image(camera_id: str = "cam_01", detect_objects: list[str] | None = None) -> dict:
    """摄像头采集图像并检测目标."""
    return {
        "image_captured": True,
        "resolution": "1920x1080",
        "objects_detected": [
            {"label": "person", "confidence": 0.95, "bbox": [100, 200, 300, 500]},
            {"label": "smoke", "confidence": 0.87, "bbox": [400, 100, 600, 350]},
        ],
    }


async def _search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """从知识库检索相关文档."""
    return {
        "query": query,
        "results": [
            {"title": "火灾应急预案 v2.1", "relevance": 0.94, "snippet": "烟雾浓度超过阈值时立即触发告警..."},
            {"title": "实验楼安全规范", "relevance": 0.88, "snippet": "温度超过60°C需启动消防系统..."},
            {"title": "维护记录 #1024", "relevance": 0.82, "snippet": "上次传感器校准: 2026-05-01..."},
        ],
    }


async def _send_alert(message: str, severity: str = "info", recipients: list[str] | None = None) -> dict:
    """发送告警通知."""
    return {
        "sent": True,
        "message": message,
        "severity": severity,
        "recipients": recipients or ["admin"],
        "channel": "sms+push",
    }


async def _control_device(device: str, action: str = "status") -> dict:
    """控制设备 (消防系统、门禁、通风等)."""
    return {"device": device, "action": action, "success": True, "message": f"{device} 已{action}"}


async def _d2d_communicate(target_device: str, purpose: str = "data_share", data: dict | None = None) -> dict:
    """D2D 设备间通信."""
    return {"connected": True, "target": target_device, "purpose": purpose, "latency_ms": 5.2}


async def _analyze_data(data: dict, analysis_type: str = "anomaly_detection") -> dict:
    """数据分析与推理."""
    return {
        "analysis_type": analysis_type,
        "findings": [
            {"type": "anomaly", "description": "烟雾浓度异常升高", "severity": "high", "confidence": 0.92},
            {"type": "trend", "description": "温度呈上升趋势", "confidence": 0.85},
        ],
        "recommendation": "建议立即启动消防告警并疏散人员",
    }


async def _web_search(query: str) -> dict:
    """网络搜索."""
    return {"query": query, "results": [{"title": "搜索结果", "snippet": "..."}]}


# ============================================================================
# 内置工具定义
# ============================================================================

BUILTIN_TOOLS: list[ToolDef] = [
    ToolDef(
        name="read_sensor",
        description="读取指定传感器的当前数据（温度、湿度、烟雾浓度等）",
        parameters={
            "type": "object",
            "properties": {
                "sensor_type": {"type": "string", "enum": ["temperature", "humidity", "smoke", "motion", "light"]},
                "location": {"type": "string", "description": "传感器位置"},
            },
            "required": ["sensor_type"],
        },
        handler=_read_sensor,
    ),
    ToolDef(
        name="capture_image",
        description="使用摄像头采集图像，进行目标检测（人员、烟雾、火焰等）",
        parameters={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string"},
                "detect_objects": {"type": "array", "items": {"type": "string"}},
            },
            "required": [],
        },
        handler=_capture_image,
    ),
    ToolDef(
        name="search_knowledge_base",
        description="从知识库检索相关文档（维护记录、安全规范、应急预案等）",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 3},
            },
            "required": ["query"],
        },
        handler=_search_knowledge_base,
    ),
    ToolDef(
        name="send_alert",
        description="向指定人员或系统发送告警通知",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                "recipients": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["message", "severity"],
        },
        handler=_send_alert,
    ),
    ToolDef(
        name="control_device",
        description="控制建筑设备（消防系统、门禁、通风、照明等）",
        parameters={
            "type": "object",
            "properties": {
                "device": {"type": "string", "enum": ["fire_system", "door_lock", "ventilation", "lighting", "elevator"]},
                "action": {"type": "string", "enum": ["activate", "deactivate", "status"]},
            },
            "required": ["device", "action"],
        },
        handler=_control_device,
    ),
    ToolDef(
        name="d2d_communicate",
        description="与邻近终端设备进行 D2D 直连通信",
        parameters={
            "type": "object",
            "properties": {
                "target_device": {"type": "string"},
                "data": {"type": "object"},
                "purpose": {"type": "string", "enum": ["data_share", "collab_sense", "relay"]},
            },
            "required": ["target_device", "purpose"],
        },
        handler=_d2d_communicate,
    ),
    ToolDef(
        name="analyze_data",
        description="对采集的数据进行分析推理（趋势判断、异常检测等）",
        parameters={
            "type": "object",
            "properties": {
                "data": {"type": "object"},
                "analysis_type": {"type": "string", "enum": ["anomaly_detection", "trend_analysis", "risk_assessment"]},
            },
            "required": ["data", "analysis_type"],
        },
        handler=_analyze_data,
    ),
    ToolDef(
        name="web_search",
        description="搜索互联网获取最新信息（仅云端可用）",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        handler=_web_search,
    ),
]


# ============================================================================
# 预定义工具组
# ============================================================================

TERMINAL_TOOL_NAMES = ["read_sensor", "capture_image"]
EDGE_TOOL_NAMES = ["read_sensor", "capture_image", "search_knowledge_base", "analyze_data", "send_alert"]
CLOUD_TOOL_NAMES = ["read_sensor", "capture_image", "search_knowledge_base", "analyze_data", "send_alert", "control_device", "web_search"]
PEER_TOOL_NAMES = ["read_sensor", "capture_image", "d2d_communicate", "analyze_data"]


def create_default_tool_registry() -> ToolRegistry:
    """创建默认工具注册表."""
    registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    registry.register_group("terminal", TERMINAL_TOOL_NAMES)
    registry.register_group("edge", EDGE_TOOL_NAMES)
    registry.register_group("cloud", CLOUD_TOOL_NAMES)
    registry.register_group("peer", PEER_TOOL_NAMES)
    return registry


# ============================================================================
# 向后兼容: 旧的列表式工具导出
# ============================================================================

# 旧代码可能还在用这些，保留但标记为 deprecated
TERMINAL_TOOLS = [t for t in BUILTIN_TOOLS if t.name in TERMINAL_TOOL_NAMES]
EDGE_TOOLS = [t for t in BUILTIN_TOOLS if t.name in EDGE_TOOL_NAMES]
CLOUD_TOOLS = [t for t in BUILTIN_TOOLS if t.name in CLOUD_TOOL_NAMES]
PEER_TOOLS = [t for t in BUILTIN_TOOLS if t.name in PEER_TOOL_NAMES]


def tools_to_openai_schema(tools: list) -> list[dict]:
    """将工具列表转换为 OpenAI tools schema."""
    return [t.to_openai_tool() for t in tools]


def tools_by_name(tools: list) -> dict[str, Any]:
    """按名称索引工具."""
    return {t.name: t for t in tools}
