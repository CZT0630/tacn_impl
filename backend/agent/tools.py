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
# 内置工具实现 — IoT 场景 (从 DataPool 读取真实数据)
# ============================================================================


def _get_datapool():
    """获取 DataPool 单例."""
    from backend.core.datapool import DataPool
    return DataPool.get_instance()


# 默认阈值配置
_SENSOR_THRESHOLDS = {
    "temperature": {"warning": 50, "critical": 60, "unit": "°C"},
    "humidity": {"warning": 70, "critical": 80, "unit": "%"},
    "smoke": {"warning": 0.05, "critical": 0.10, "unit": "ppm"},
    "motion": {"unit": "bool"},
    "light": {"unit": "lux"},
}


async def _read_sensor(sensor_type: str = "temperature", location: str = "未知位置") -> dict:
    """读取传感器数据 — 从 DataPool 获取真实值."""
    pool = _get_datapool()

    # 尝试从多个可能的 source 读取
    sources = [f"sensor_{location}", f"sensor_{sensor_type}", "sensor_default"]
    value = None
    matched_source = None
    for src in sources:
        v = pool.get_latest_value(src, sensor_type)
        if v is not None:
            value = v
            matched_source = src
            break

    if value is None:
        # DataPool 无数据时，返回提示（非硬编码 mock）
        return {
            "sensor_type": sensor_type,
            "location": location,
            "data": None,
            "status": "no_data",
            "message": f"传感器 {sensor_type}@{location} 暂无数据，请通过 POST /api/data/push 灌入",
        }

    # 判断阈值状态
    thresholds = _SENSOR_THRESHOLDS.get(sensor_type, {})
    status = "normal"
    if "critical" in thresholds and isinstance(value, (int, float)):
        if value >= thresholds["critical"]:
            status = "CRITICAL"
        elif value >= thresholds["warning"]:
            status = "warning"

    return {
        "sensor_type": sensor_type,
        "location": location,
        "source": matched_source,
        "data": {
            "value": value,
            "unit": thresholds.get("unit", ""),
            "threshold": thresholds.get("critical"),
            "status": status,
        },
    }


async def _capture_image(camera_id: str = "cam_01", detect_objects: list[str] | None = None) -> dict:
    """摄像头采集图像 — 从 DataPool 获取检测结果."""
    pool = _get_datapool()

    # 从 DataPool 读取摄像头数据
    data = pool.get_latest_value(f"camera_{camera_id}", "detection")
    if data is not None:
        return data

    # 读取原始图像 URL
    image_url = pool.get_latest_value(f"camera_{camera_id}", "image")
    if image_url is not None:
        return {
            "camera_id": camera_id,
            "image_url": image_url,
            "objects_detected": [],
            "message": "图像已获取，但无检测结果。请通过 POST /api/data/push 推送 detection 数据",
        }

    return {
        "camera_id": camera_id,
        "image_captured": False,
        "status": "no_data",
        "message": f"摄像头 {camera_id} 暂无数据，请通过 POST /api/data/push 灌入",
    }


async def _search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """从知识库检索 — 从 DataPool 获取文档."""
    pool = _get_datapool()

    # 从 DataPool 读取知识库数据
    docs = pool.get_latest_value("knowledge_base", "documents")
    if docs is None:
        docs = pool.get_latest_value("kb", "documents")

    if docs is not None and isinstance(docs, list):
        # 简单关键词匹配 (真实场景应使用向量检索)
        query_lower = query.lower()
        scored = []
        for doc in docs:
            text = json.dumps(doc, ensure_ascii=False).lower()
            # 计算简单的关键词命中率
            keywords = query_lower.split()
            hits = sum(1 for kw in keywords if kw in text)
            if hits > 0:
                scored.append((hits / len(keywords), doc))
        scored.sort(key=lambda x: -x[0])
        return {
            "query": query,
            "results": [
                {
                    "title": d.get("title", ""),
                    "relevance": round(score, 2),
                    "snippet": d.get("content", d.get("snippet", ""))[:200],
                }
                for score, d in scored[:top_k]
            ],
        }

    return {
        "query": query,
        "results": [],
        "status": "no_data",
        "message": "知识库为空，请通过 POST /api/data/push 推送 source=knowledge_base, type=documents",
    }


async def _send_alert(message: str, severity: str = "info", recipients: list[str] | None = None) -> dict:
    """发送告警通知 — 记录到 DataPool."""
    pool = _get_datapool()
    alert_data = {
        "message": message,
        "severity": severity,
        "recipients": recipients or ["admin"],
        "sent": True,
        "channel": "sms+push",
        "ts": __import__("time").time(),
    }
    # 记录到 DataPool (供前端展示告警历史)
    pool.push("system", "alert", alert_data)
    return alert_data


async def _control_device(device: str, action: str = "status") -> dict:
    """控制设备 — 记录到 DataPool."""
    pool = _get_datapool()
    result = {"device": device, "action": action, "success": True, "message": f"{device} 已{action}"}
    pool.push("system", "device_control", result)
    return result


async def _d2d_communicate(target_device: str, purpose: str = "data_share", data: dict | None = None) -> dict:
    """D2D 设备间通信."""
    return {"connected": True, "target": target_device, "purpose": purpose, "latency_ms": 5.2}


async def _analyze_data(data: dict, analysis_type: str = "anomaly_detection") -> dict:
    """数据分析与推理 — 从输入数据中分析."""
    if not data:
        pool = _get_datapool()
        # 尝试从 DataPool 获取待分析数据
        sensor_snapshot = pool.get_all_latest()
        if sensor_snapshot:
            data = sensor_snapshot
        else:
            return {
                "analysis_type": analysis_type,
                "findings": [],
                "message": "无数据可分析，请提供 data 参数或通过 DataPool 灌入传感器数据",
            }

    # 基于规则的简单分析
    findings = []
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, dict):
                status = val.get("status", "")
                if status in ("CRITICAL", "ALERT"):
                    findings.append({
                        "type": "anomaly",
                        "description": f"{key} 状态异常: {status}",
                        "severity": "high",
                        "confidence": 0.9,
                    })
                elif status == "warning":
                    findings.append({
                        "type": "warning",
                        "description": f"{key} 状态告警: {status}",
                        "severity": "medium",
                        "confidence": 0.8,
                    })

    recommendation = "建议立即处理" if findings else "数据正常，无需处理"
    return {
        "analysis_type": analysis_type,
        "data_keys": list(data.keys()) if isinstance(data, dict) else [],
        "findings": findings,
        "recommendation": recommendation,
    }


async def _web_search(query: str) -> dict:
    """网络搜索 (仅云端可用)."""
    return {"query": query, "results": [{"title": "搜索结果 (需配置外部 API)", "snippet": "..."}]}


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
