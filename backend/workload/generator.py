"""工作负载生成器 - 生成测试请求."""

from __future__ import annotations

import random
from typing import Optional

from backend.core.models import IntentType


# 请求模板
REQUEST_TEMPLATES: dict[IntentType, list[str]] = {
    IntentType.EMERGENCY_RESPONSE: [
        "实验楼烟雾传感器报警，请结合摄像头画面、维护记录和安全规范判断是否触发消防告警",
        "检测到火警信号，请立即启动应急响应流程并通知附近人员",
        "A区烟雾浓度超标，请分析传感器数据并确认是否为真实火情",
        "消防系统报警，请结合多源传感器数据进行综合判断",
        "B栋3楼烟感器触发，请调取监控画面并联系维保人员",
    ],
    IntentType.ROBOT_INSPECTION: [
        "巡检机器人发现设备温度异常，请检查维护记录并给出维护建议",
        "请对A区设备进行全面巡检并生成巡检报告",
        "机器人检测到异常振动，请分析历史数据并预测故障风险",
        "设备运行状态异常，请结合传感器数据和维护记录进行诊断",
        "巡检发现设备外观损伤，请评估损伤程度并制定维修方案",
    ],
    IntentType.SECURITY_MONITORING: [
        "多个摄像头检测到异常行为，请分析并通知安保人员",
        "C区检测到未授权人员进入，请调取监控并核实身份",
        "停车场监控发现可疑车辆，请进行行为分析并预警",
        "园区周界检测到异常活动，请启动安防响应程序",
        "办公楼入口检测到尾随进入行为，请分析并通知安保",
    ],
    IntentType.PREDICTIVE_MAINTENANCE: [
        "根据历史数据和实时状态预测设备故障风险",
        "分析设备运行数据，预测未来一周的故障概率",
        "请基于传感器数据预测设备剩余使用寿命",
        "综合分析设备历史数据，生成预测性维护建议",
        "评估设备健康状态，预测潜在故障点",
    ],
    IntentType.MEETING_ASSISTANT: [
        "请帮我安排明天下午的技术评审会议，通知相关人员",
        "协调本周的项目进度会议，找一个大家都有空的时间",
        "安排与客户的线上会议，准备相关材料和议程",
        "组织部门周会，收集各部门进度汇报",
        "安排新员工培训会议，邀请相关导师参加",
    ],
}


class WorkloadGenerator:
    """工作负载生成器.

    生成复杂用户请求用于测试.
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate(self, intent_type: IntentType, count: int) -> list[str]:
        """生成指定类型的请求.

        Args:
            intent_type: 意图类型
            count: 数量

        Returns:
            请求列表
        """
        templates = REQUEST_TEMPLATES.get(intent_type, [])
        if not templates:
            return []

        return random.choices(templates, k=count)

    def generate_mixed(self, count: int) -> list[str]:
        """生成混合类型的请求.

        Args:
            count: 总数量

        Returns:
            请求列表
        """
        requests = []
        intent_types = list(IntentType)

        for _ in range(count):
            intent_type = random.choice(intent_types)
            templates = REQUEST_TEMPLATES.get(intent_type, [])
            if templates:
                requests.append(random.choice(templates))

        return requests

    def generate_with_metadata(self, intent_type: IntentType, count: int) -> list[dict]:
        """生成带元数据的请求.

        Args:
            intent_type: 意图类型
            count: 数量

        Returns:
            带元数据的请求列表
        """
        requests = self.generate(intent_type, count)

        result = []
        for req in requests:
            result.append({
                "request": req,
                "intent_type": intent_type.value,
                "expected_intent": intent_type,
            })

        return result

    def get_all_templates(self) -> dict[str, list[str]]:
        """获取所有模板."""
        return {k.value: v for k, v in REQUEST_TEMPLATES.items()}
