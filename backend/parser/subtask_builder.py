"""子任务图构建器 - 基于LLM将意图分解为子任务DAG."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from backend.core.models import (
    CapabilityRequirement,
    CapabilityType,
    Intent,
    IntentType,
    SubTask,
    SubTaskEdge,
    SubTaskGraph,
)
from backend.parser.json_repair import repair_json_output
from backend.parser.validators import SubTaskGraphOutput

if TYPE_CHECKING:
    from backend.llm.client import LLMClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个任务分解专家。将用户意图分解为子任务图(DAG)。

输出格式（严格JSON）:
{
  "subtasks": [
    {
      "name": "子任务名称(英文snake_case)",
      "description": "子任务描述",
      "capabilities": ["sensing", "vision", ...],
      "tools": ["camera", ...],
      "priority": 10,
      "estimated_computation": 100,
      "estimated_data_size_kb": 50
    }
  ],
  "dependencies": [
    ["子任务A名称", "子任务B名称"]
  ]
}

规则:
1. 子任务之间通过dependencies表达依赖关系: [A, B] 表示A完成后才能执行B
2. 无依赖的子任务可以并行执行
3. 每个子任务标注所需的能力和工具
4. priority: 1-10, 10最高
5. estimated_computation: 预估计算量(相对值)
6. estimated_data_size_kb: 预估数据量(KB)

只输出JSON，不要其他文字。"""


class LLMSubTaskBuilder:
    """基于LLM的子任务图分解器."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    async def build(self, intent: Intent) -> SubTaskGraph:
        """LLM将Intent分解为子任务DAG.

        流程:
        1. 有 LLM → 调用 LLM + JSON 修复 + Pydantic 验证
        2. 失败或无 LLM → 回退到默认模板

        Args:
            intent: 解析后的意图

        Returns:
            子任务依赖图
        """
        if self.llm_client is not None:
            graph = await self._build_with_llm(intent)
            if graph is not None:
                return graph
            logger.warning("LLM 子任务分解失败，回退到默认模板")

        return self._default_build(intent)

    async def _build_with_llm(self, intent: Intent) -> SubTaskGraph | None:
        """用 LLM 分解子任务 + JSON 修复 + Pydantic 验证."""
        try:
            caps = [c.capability_type.value for c in intent.required_capabilities]

            user_prompt = f"""请将以下意图分解为子任务图(DAG):

意图类型: {intent.intent_type.value}
所需能力: {caps}
所需工具: {intent.required_tools}
隐私级别: {intent.privacy_level.value}
是否需要协作: {intent.requires_collaboration}"""

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            response = await self.llm_client.chat(messages)

            if not response.content:
                return None

            # JSON 修复管道
            repaired = repair_json_output(response.content)
            if not repaired.strip().startswith(("{", "[")):
                logger.warning("子任务分解 LLM 输出不是有效的 JSON")
                return None

            # Pydantic 验证
            parsed = SubTaskGraphOutput.model_validate_json(repaired)
            if not parsed.subtasks:
                return None

            return self._validated_to_subtask_graph(intent, parsed)

        except Exception as e:
            logger.debug(f"LLM 子任务分解失败: {e}")
            return None

    def _validated_to_subtask_graph(
        self, intent: Intent, parsed: SubTaskGraphOutput
    ) -> SubTaskGraph:
        """将 Pydantic 验证后的结果转为 SubTaskGraph."""
        cap_type_map = {v.value: v for v in CapabilityType}

        subtasks = []
        name_to_id = {}

        for st_def in parsed.subtasks:
            capabilities = []
            for cap_str in st_def.capabilities:
                cap_type = cap_type_map.get(cap_str)
                if cap_type:
                    capabilities.append(
                        CapabilityRequirement(
                            capability_type=cap_type, min_quality=0.7
                        )
                    )

            subtask = SubTask(
                name=st_def.name,
                description=st_def.description,
                required_capabilities=capabilities,
                required_tools=st_def.tools,
                estimated_computation=st_def.estimated_computation,
                estimated_data_size_kb=st_def.estimated_data_size_kb,
                priority=st_def.priority,
                privacy_level=intent.privacy_level,
            )
            subtasks.append(subtask)
            name_to_id[subtask.name] = subtask.id

        edges = []
        for dep in parsed.dependencies:
            if len(dep) == 2:
                source_name, target_name = dep
                if source_name in name_to_id and target_name in name_to_id:
                    edges.append(
                        SubTaskEdge(
                            source_id=name_to_id[source_name],
                            target_id=name_to_id[target_name],
                            dependency_type="data",
                        )
                    )

        return SubTaskGraph(
            intent_id=intent.id, subtasks=subtasks, edges=edges
        )

    def _default_build(self, intent: Intent) -> SubTaskGraph:
        """默认子任务分解 - 当LLM不可用时的回退."""
        templates = {
            IntentType.EMERGENCY_RESPONSE: [
                ("sensor_analysis", "分析传感器数据", [CapabilityType.SENSING], ["smoke_detector"], 10),
                ("vision_confirm", "通过摄像头确认现场", [CapabilityType.VISION], ["camera"], 9),
                ("rule_reasoning", "应用安全规则推理", [CapabilityType.REASONING], [], 8),
                ("alarm_decision", "决定是否触发告警", [CapabilityType.REASONING], [], 10),
                ("notify_staff", "通知相关人员", [CapabilityType.NOTIFICATION], [], 9),
            ],
            IntentType.ROBOT_INSPECTION: [
                ("device_status_check", "检查设备状态", [CapabilityType.SENSING], ["temperature_sensor"], 8),
                ("visual_inspection", "视觉检测", [CapabilityType.VISION], ["camera"], 7),
                ("history_retrieval", "检索维护记录", [CapabilityType.RAG_RETRIEVAL], ["document_store"], 6),
                ("anomaly_detection", "检测异常", [CapabilityType.REASONING], [], 8),
                ("maintenance_suggestion", "生成维护建议", [CapabilityType.REASONING, CapabilityType.PLANNING], [], 7),
            ],
            IntentType.SECURITY_MONITORING: [
                ("video_collection", "采集视频流", [CapabilityType.VISION], ["camera"], 9),
                ("person_detection", "检测人员", [CapabilityType.VISION], [], 8),
                ("behavior_analysis", "分析行为模式", [CapabilityType.REASONING], [], 8),
                ("alert_decision", "决定是否告警", [CapabilityType.REASONING], [], 10),
                ("security_notify", "通知安保", [CapabilityType.NOTIFICATION], [], 9),
            ],
            IntentType.PREDICTIVE_MAINTENANCE: [
                ("data_collection", "采集实时数据", [CapabilityType.SENSING], ["temperature_sensor"], 8),
                ("history_retrieval", "检索历史数据", [CapabilityType.RAG_RETRIEVAL], ["document_store"], 7),
                ("fault_prediction", "预测故障", [CapabilityType.REASONING], [], 9),
                ("maintenance_planning", "生成维护计划", [CapabilityType.PLANNING], [], 7),
            ],
            IntentType.MEETING_ASSISTANT: [
                ("schedule_retrieval", "检索日程", [CapabilityType.RAG_RETRIEVAL], ["document_store"], 7),
                ("location_planning", "规划会议位置", [CapabilityType.PLANNING], [], 6),
                ("participant_notification", "通知参会人", [CapabilityType.NOTIFICATION], [], 8),
            ],
        }

        dep_templates = {
            IntentType.EMERGENCY_RESPONSE: [
                ("sensor_analysis", "rule_reasoning"),
                ("vision_confirm", "rule_reasoning"),
                ("rule_reasoning", "alarm_decision"),
                ("alarm_decision", "notify_staff"),
            ],
            IntentType.ROBOT_INSPECTION: [
                ("device_status_check", "anomaly_detection"),
                ("visual_inspection", "anomaly_detection"),
                ("history_retrieval", "anomaly_detection"),
                ("anomaly_detection", "maintenance_suggestion"),
            ],
            IntentType.SECURITY_MONITORING: [
                ("video_collection", "person_detection"),
                ("person_detection", "behavior_analysis"),
                ("behavior_analysis", "alert_decision"),
                ("alert_decision", "security_notify"),
            ],
            IntentType.PREDICTIVE_MAINTENANCE: [
                ("data_collection", "fault_prediction"),
                ("history_retrieval", "fault_prediction"),
                ("fault_prediction", "maintenance_planning"),
            ],
            IntentType.MEETING_ASSISTANT: [
                ("schedule_retrieval", "location_planning"),
                ("location_planning", "participant_notification"),
            ],
        }

        st_defs = templates.get(intent.intent_type, templates[IntentType.MEETING_ASSISTANT])
        dep_defs = dep_templates.get(intent.intent_type, [])

        subtasks = []
        name_to_id = {}
        for name, desc, caps, tools, priority in st_defs:
            st = SubTask(
                name=name,
                description=desc,
                required_capabilities=[CapabilityRequirement(capability_type=c, min_quality=0.7) for c in caps],
                required_tools=tools,
                priority=priority,
                privacy_level=intent.privacy_level,
            )
            subtasks.append(st)
            name_to_id[name] = st.id

        edges = []
        for src, tgt in dep_defs:
            if src in name_to_id and tgt in name_to_id:
                edges.append(SubTaskEdge(source_id=name_to_id[src], target_id=name_to_id[tgt]))

        return SubTaskGraph(intent_id=intent.id, subtasks=subtasks, edges=edges)

    def get_critical_path(self, graph: SubTaskGraph) -> list[str]:
        """计算关键路径."""
        if not graph.subtasks:
            return []

        adj = {st.id: [] for st in graph.subtasks}
        in_degree = {st.id: 0 for st in graph.subtasks}
        for edge in graph.edges:
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1

        dist = {st.id: 0.0 for st in graph.subtasks}
        prev = {st.id: None for st in graph.subtasks}
        queue = [st.id for st in graph.subtasks if in_degree[st.id] == 0]

        while queue:
            node = queue.pop(0)
            node_st = graph.get_subtask(node)
            if not node_st:
                continue
            duration = node_st.estimated_computation * 0.5 + node_st.estimated_data_size_kb * 0.1
            for neighbor in adj[node]:
                if dist[node] + duration > dist[neighbor]:
                    dist[neighbor] = dist[node] + duration
                    prev[neighbor] = node
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if not dist:
            return []
        end_node = max(dist, key=lambda x: dist[x])
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = prev[current]
        return list(reversed(path))
