"""意图解析器 - 基于LLM将自然语言转换为结构化意图.

参考 deer-flow coordinator 节点的设计:
- 优先用 tool-calling 做结构化分类（输出空间被 schema 约束）
- 不支持 tool-calling 时回退到自由文本 JSON 解析 + Pydantic 验证
- 无 LLM 时用关键词匹配兜底
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Optional

from backend.core.models import (
    CapabilityRequirement,
    CapabilityType,
    Intent,
    IntentType,
    PrivacyLevel,
)
from backend.parser.json_repair import repair_json_output
from backend.parser.validators import IntentOutput

if TYPE_CHECKING:
    from backend.llm.client import LLMClient

logger = logging.getLogger(__name__)


# ============================================================================
# 映射表
# ============================================================================

INTENT_TYPE_MAP: dict[str, IntentType] = {
    "emergency_response": IntentType.EMERGENCY_RESPONSE,
    "robot_inspection": IntentType.ROBOT_INSPECTION,
    "security_monitoring": IntentType.SECURITY_MONITORING,
    "predictive_maintenance": IntentType.PREDICTIVE_MAINTENANCE,
    "meeting_assistant": IntentType.MEETING_ASSISTANT,
}

CAPABILITY_MAP: dict[str, CapabilityType] = {
    "sensing": CapabilityType.SENSING,
    "vision": CapabilityType.VISION,
    "audio": CapabilityType.AUDIO,
    "reasoning": CapabilityType.REASONING,
    "planning": CapabilityType.PLANNING,
    "tool_calling": CapabilityType.TOOL_CALLING,
    "rag_retrieval": CapabilityType.RAG_RETRIEVAL,
    "notification": CapabilityType.NOTIFICATION,
    "control": CapabilityType.CONTROL,
    "computation": CapabilityType.COMPUTATION,
    "communication": CapabilityType.COMMUNICATION,
}

PRIVACY_MAP: dict[str, PrivacyLevel] = {
    "public": PrivacyLevel.PUBLIC,
    "internal": PrivacyLevel.INTERNAL,
    "confidential": PrivacyLevel.CONFIDENTIAL,
    "restricted": PrivacyLevel.RESTRICTED,
}

DEFAULT_DEADLINES: dict[IntentType, float] = {
    IntentType.EMERGENCY_RESPONSE: 5000,
    IntentType.SECURITY_MONITORING: 10000,
    IntentType.ROBOT_INSPECTION: 30000,
    IntentType.PREDICTIVE_MAINTENANCE: 60000,
    IntentType.MEETING_ASSISTANT: 300000,
}


# ============================================================================
# Tool-calling 定义 (参考 deer-flow coordinator)
# ============================================================================

INTENT_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "handoff_to_emergency",
            "description": "应急响应：火灾、烟雾、泄漏、事故等紧急事件需要立即处理",
            "parameters": {
                "type": "object",
                "properties": {
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需能力: sensing, vision, reasoning, notification",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需工具: camera, smoke_detector, temperature_sensor",
                    },
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                        "description": "隐私级别",
                    },
                    "deadline_ms": {
                        "type": "number",
                        "description": "截止时间(毫秒)",
                    },
                    "requires_collaboration": {
                        "type": "boolean",
                        "description": "是否需要多智能体协作",
                    },
                },
                "required": ["capabilities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_inspection",
            "description": "机器人巡检：设备状态检查、温度异常、定期巡检",
            "parameters": {
                "type": "object",
                "properties": {
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需能力: sensing, vision, rag_retrieval, reasoning",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需工具: temperature_sensor, camera, document_store",
                    },
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                    },
                    "deadline_ms": {"type": "number"},
                    "requires_collaboration": {"type": "boolean"},
                },
                "required": ["capabilities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_security",
            "description": "安防监控：异常人员检测、入侵检测、行为分析",
            "parameters": {
                "type": "object",
                "properties": {
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需能力: vision, reasoning, notification",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需工具: camera",
                    },
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                    },
                    "deadline_ms": {"type": "number"},
                    "requires_collaboration": {"type": "boolean"},
                },
                "required": ["capabilities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_maintenance",
            "description": "预测性维护：设备故障预测、维护规划、历史数据分析",
            "parameters": {
                "type": "object",
                "properties": {
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需能力: sensing, rag_retrieval, reasoning, planning",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需工具: temperature_sensor, document_store",
                    },
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                    },
                    "deadline_ms": {"type": "number"},
                    "requires_collaboration": {"type": "boolean"},
                },
                "required": ["capabilities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_meeting",
            "description": "会议助手：日程安排、会议记录、参会人通知",
            "parameters": {
                "type": "object",
                "properties": {
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需能力: rag_retrieval, planning, notification",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所需工具: document_store",
                    },
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                    },
                    "deadline_ms": {"type": "number"},
                    "requires_collaboration": {"type": "boolean"},
                },
                "required": ["capabilities"],
            },
        },
    },
]

# tool name -> IntentType 映射
_TOOL_TO_INTENT: dict[str, IntentType] = {
    "handoff_to_emergency": IntentType.EMERGENCY_RESPONSE,
    "handoff_to_inspection": IntentType.ROBOT_INSPECTION,
    "handoff_to_security": IntentType.SECURITY_MONITORING,
    "handoff_to_maintenance": IntentType.PREDICTIVE_MAINTENANCE,
    "handoff_to_meeting": IntentType.MEETING_ASSISTANT,
}


# ============================================================================
# System Prompt (自由文本模式使用)
# ============================================================================

SYSTEM_PROMPT = """你是一个意图解析专家。分析用户请求，输出JSON格式的结构化意图。

输出格式（严格JSON）:
{
  "intent_type": "emergency_response|robot_inspection|security_monitoring|predictive_maintenance|meeting_assistant",
  "capabilities": ["sensing", "vision", "reasoning", "notification", ...],
  "tools": ["camera", "smoke_detector", "temperature_sensor", ...],
  "privacy_level": "public|internal|confidential",
  "deadline_ms": 5000,
  "context_needs": ["maintenance_records", "sensor_history", ...],
  "requires_collaboration": true|false
}

能力类型说明:
- sensing: 传感器数据采集
- vision: 视觉分析
- audio: 音频处理
- reasoning: 推理判断
- planning: 规划调度
- tool_calling: 工具调用
- rag_retrieval: 知识检索
- notification: 通知告警
- control: 设备控制
- computation: 计算处理
- communication: 通信协调

只输出JSON，不要其他文字。"""


# ============================================================================
# 意图解析器
# ============================================================================


class LLMIntentParser:
    """基于LLM的意图解析器.

    解析流程 (参考 deer-flow coordinator):
    1. 优先 tool-calling 分类（结构化约束，不会格式错误）
    2. 回退到自由文本 JSON 解析 + Pydantic 验证
    3. 无 LLM 时用关键词匹配兜底
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    async def parse(
        self, text: str, deadline_ms: Optional[float] = None
    ) -> Intent:
        """解析自然语言请求为结构化 Intent.

        Args:
            text: 自然语言请求
            deadline_ms: 截止时间(毫秒), None则由LLM决定

        Returns:
            解析后的 Intent 对象
        """
        # 无 LLM → 关键词 mock
        if self.llm_client is None:
            return self._parse_with_mock(text, deadline_ms)

        # 尝试 tool-calling 分类
        intent = await self._parse_with_tool_calling(text, deadline_ms)
        if intent is not None:
            return intent

        # 回退到自由文本 JSON 解析
        intent = await self._parse_with_json(text, deadline_ms)
        if intent is not None:
            return intent

        # 全部失败 → 关键词兜底
        logger.warning("LLM 意图解析全部失败，回退到关键词匹配")
        return self._parse_with_mock(text, deadline_ms)

    # ------------------------------------------------------------------
    # 模式1: Tool-calling 分类 (参考 deer-flow coordinator)
    # ------------------------------------------------------------------

    async def _parse_with_tool_calling(
        self, text: str, deadline_ms: Optional[float]
    ) -> Intent | None:
        """用 tool-calling 做结构化分类."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个意图分析专家。根据用户请求，选择最匹配的意图类型。"
                        "你需要从可用的工具中选择一个来分类用户意图。"
                    ),
                },
                {"role": "user", "content": text},
            ]
            response = await self.llm_client.chat(
                messages, tools=INTENT_TOOLS, tool_choice="required"
            )

            if not response.tool_calls:
                return None

            tc = response.tool_calls[0]
            intent_type = _TOOL_TO_INTENT.get(tc.name)
            if intent_type is None:
                logger.warning(f"未知的 tool name: {tc.name}")
                return None

            # 从 tool arguments 提取参数
            args = tc.arguments
            capabilities = args.get("capabilities", [])
            tools = args.get("tools", [])
            privacy_str = args.get("privacy_level", "internal")
            tc_deadline = args.get("deadline_ms")
            requires_collab = args.get("requires_collaboration", False)

            # 构建 Intent
            cap_requirements = self._resolve_capabilities(capabilities, intent_type)
            privacy_level = PRIVACY_MAP.get(privacy_str, PrivacyLevel.INTERNAL)
            if deadline_ms is None:
                deadline_ms = tc_deadline or DEFAULT_DEADLINES.get(intent_type, 30000)

            return Intent(
                text=text,
                intent_type=intent_type,
                required_capabilities=cap_requirements,
                required_tools=tools,
                deadline_ms=deadline_ms,
                privacy_level=privacy_level,
                requires_collaboration=requires_collab,
                metadata={"parser": "llm_tool_calling"},
            )

        except Exception as e:
            logger.debug(f"Tool-calling 解析失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 模式2: 自由文本 JSON 解析
    # ------------------------------------------------------------------

    async def _parse_with_json(
        self, text: str, deadline_ms: Optional[float]
    ) -> Intent | None:
        """用自由文本 + JSON 解析 + Pydantic 验证."""
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ]
            response = await self.llm_client.chat(messages)

            if not response.content:
                return None

            # JSON 修复管道
            repaired = repair_json_output(response.content)
            if not repaired.strip().startswith(("{", "[")):
                logger.warning("LLM 输出不是有效的 JSON 结构")
                return None

            # Pydantic 验证
            parsed = IntentOutput.model_validate_json(repaired)
            return self._validated_to_intent(text, parsed, deadline_ms)

        except Exception as e:
            logger.debug(f"JSON 解析失败: {e}")
            return None

    def _validated_to_intent(
        self, text: str, parsed: IntentOutput, deadline_ms: Optional[float]
    ) -> Intent:
        """将 Pydantic 验证后的结果转为 Intent."""
        intent_type = INTENT_TYPE_MAP.get(parsed.intent_type, IntentType.MEETING_ASSISTANT)

        cap_requirements = self._resolve_capabilities(parsed.capabilities, intent_type)
        privacy_level = PRIVACY_MAP.get(parsed.privacy_level, PrivacyLevel.INTERNAL)

        if deadline_ms is None:
            deadline_ms = parsed.deadline_ms or DEFAULT_DEADLINES.get(intent_type, 30000)

        return Intent(
            text=text,
            intent_type=intent_type,
            required_capabilities=cap_requirements,
            required_tools=parsed.tools,
            required_context=parsed.context_needs,
            deadline_ms=deadline_ms,
            privacy_level=privacy_level,
            requires_collaboration=parsed.requires_collaboration,
            metadata={"parser": "llm_json"},
        )

    # ------------------------------------------------------------------
    # 模式3: 关键词 Mock 解析 (兜底)
    # ------------------------------------------------------------------

    def _parse_with_mock(
        self, text: str, deadline_ms: Optional[float]
    ) -> Intent:
        """基于关键词的 mock 解析."""
        result = self._mock_parse(text)
        parsed = json.loads(result)
        intent_type = INTENT_TYPE_MAP.get(
            parsed.get("intent_type", ""), IntentType.MEETING_ASSISTANT
        )
        return self._to_intent_from_dict(text, parsed, intent_type, deadline_ms)

    def _mock_parse(self, text: str) -> str:
        """关键词匹配返回 JSON 字符串."""
        text_lower = text.lower()

        intent_type = "meeting_assistant"
        if re.search(r"烟雾|火警|消防|emergency|fire|报警|告警|应急", text_lower):
            intent_type = "emergency_response"
        elif re.search(r"巡检|inspection|机器人|设备检查|温度异常", text_lower):
            intent_type = "robot_inspection"
        elif re.search(r"安防|security|监控|异常人员|入侵|可疑", text_lower):
            intent_type = "security_monitoring"
        elif re.search(r"预测|predictive|故障|维护建议", text_lower):
            intent_type = "predictive_maintenance"

        capabilities = []
        cap_keywords = {
            "sensing": ["传感器", "sensor", "温度", "湿度", "烟雾"],
            "vision": ["摄像头", "camera", "视觉", "图像", "视频"],
            "reasoning": ["推理", "判断", "分析", "reasoning"],
            "notification": ["通知", "告警", "alert", "notify"],
            "rag_retrieval": ["检索", "查询", "知识库", "记录"],
            "planning": ["规划", "安排", "协调", "planning"],
        }
        for cap, keywords in cap_keywords.items():
            if any(kw in text_lower for kw in keywords):
                capabilities.append(cap)
        if not capabilities:
            capabilities = ["reasoning"]

        tools = []
        tool_keywords = {
            "camera": ["摄像头", "camera"],
            "smoke_detector": ["烟雾", "smoke"],
            "temperature_sensor": ["温度", "temperature"],
            "document_store": ["记录", "文档", "历史"],
        }
        for tool, keywords in tool_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tools.append(tool)

        privacy = (
            "confidential"
            if any(kw in text_lower for kw in ["隐私", "敏感", "private"])
            else "internal"
        )

        return json.dumps(
            {
                "intent_type": intent_type,
                "capabilities": capabilities,
                "tools": tools,
                "privacy_level": privacy,
                "requires_collaboration": intent_type
                in ["emergency_response", "security_monitoring"],
            }
        )

    # ------------------------------------------------------------------
    # 共用工具方法
    # ------------------------------------------------------------------

    def _to_intent_from_dict(
        self,
        text: str,
        parsed: dict,
        intent_type: IntentType,
        deadline_ms: Optional[float],
    ) -> Intent:
        """从字典构建 Intent (用于 mock 路径)."""
        cap_requirements = self._resolve_capabilities(
            parsed.get("capabilities", []), intent_type
        )
        privacy_level = PRIVACY_MAP.get(
            parsed.get("privacy_level", "internal"), PrivacyLevel.INTERNAL
        )
        if deadline_ms is None:
            deadline_ms = DEFAULT_DEADLINES.get(intent_type, 30000)

        return Intent(
            text=text,
            intent_type=intent_type,
            required_capabilities=cap_requirements,
            required_tools=parsed.get("tools", []),
            deadline_ms=deadline_ms,
            privacy_level=privacy_level,
            requires_collaboration=parsed.get("requires_collaboration", False),
            metadata={"parser": "mock"},
        )

    def _resolve_capabilities(
        self, cap_strs: list[str], intent_type: IntentType
    ) -> list[CapabilityRequirement]:
        """解析能力字符串列表为 CapabilityRequirement.

        无效的能力名会被跳过，如果全部无效则根据意图类型推断。
        """
        requirements = []
        for cap_str in cap_strs:
            cap_type = CAPABILITY_MAP.get(cap_str)
            if cap_type:
                requirements.append(
                    CapabilityRequirement(capability_type=cap_type, min_quality=0.7)
                )

        if not requirements:
            requirements = self._infer_capabilities(intent_type)

        return requirements

    def _infer_capabilities(
        self, intent_type: IntentType
    ) -> list[CapabilityRequirement]:
        """根据意图类型推断默认能力需求."""
        infer_map = {
            IntentType.EMERGENCY_RESPONSE: [
                CapabilityType.SENSING,
                CapabilityType.VISION,
                CapabilityType.REASONING,
                CapabilityType.NOTIFICATION,
            ],
            IntentType.ROBOT_INSPECTION: [
                CapabilityType.SENSING,
                CapabilityType.VISION,
                CapabilityType.RAG_RETRIEVAL,
                CapabilityType.REASONING,
            ],
            IntentType.SECURITY_MONITORING: [
                CapabilityType.VISION,
                CapabilityType.REASONING,
                CapabilityType.NOTIFICATION,
            ],
            IntentType.PREDICTIVE_MAINTENANCE: [
                CapabilityType.SENSING,
                CapabilityType.RAG_RETRIEVAL,
                CapabilityType.REASONING,
                CapabilityType.PLANNING,
            ],
            IntentType.MEETING_ASSISTANT: [
                CapabilityType.RAG_RETRIEVAL,
                CapabilityType.PLANNING,
                CapabilityType.NOTIFICATION,
            ],
        }
        caps = infer_map.get(intent_type, [CapabilityType.REASONING])
        return [
            CapabilityRequirement(capability_type=c, min_quality=0.7) for c in caps
        ]
