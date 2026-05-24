"""信任、安全与隐私控制面."""

from __future__ import annotations

from backend.core.models import AgentProfile, PrivacyLevel, SubTask


class TrustPrivacyControlPlane:
    """信任、安全与隐私控制面.

    职责: 隐私敏感任务识别、本地数据最小化处理、数据脱敏、
    智能体身份认证、可信度评估、工具权限控制、上下文访问控制、执行审计.

    回答: 哪些数据不能离开本地？哪些智能体可信？哪些工具可以调用？
    """

    PRIVACY_ORDER = {
        PrivacyLevel.PUBLIC: 0,
        PrivacyLevel.INTERNAL: 1,
        PrivacyLevel.CONFIDENTIAL: 2,
        PrivacyLevel.RESTRICTED: 3,
    }

    def assess_privacy_risk(
        self, subtask: SubTask, agent: AgentProfile
    ) -> float:
        """评估隐私风险 (0-1，越高越危险)."""
        task_level = self.PRIVACY_ORDER.get(subtask.privacy_level, 0)
        agent_level = self.PRIVACY_ORDER.get(agent.privacy_level, 0)
        if agent_level >= task_level:
            return 0.0
        return (task_level - agent_level) / 3.0

    def is_privacy_compatible(
        self, subtask: SubTask, agent: AgentProfile
    ) -> bool:
        """检查隐私兼容性."""
        return self.assess_privacy_risk(subtask, agent) == 0.0

    def filter_sensitive_data(
        self, data: dict, privacy_level: PrivacyLevel
    ) -> dict:
        """为远程执行过滤敏感数据."""
        if privacy_level in (PrivacyLevel.RESTRICTED, PrivacyLevel.CONFIDENTIAL):
            filtered = {}
            sensitive_keys = {
                "user_id",
                "location_exact",
                "biometric",
                "password",
                "token",
                "credential",
            }
            for k, v in data.items():
                if k not in sensitive_keys:
                    filtered[k] = v
            return filtered
        return data

    def check_tool_permission(
        self,
        agent: AgentProfile,
        tool_id: str,
        required_permissions: list[str],
    ) -> bool:
        """检查工具权限."""
        if not required_permissions:
            return True
        agent_level = self.PRIVACY_ORDER.get(agent.privacy_level, 0)
        return agent_level >= 1  # 至少 INTERNAL

    def evaluate_trust(self, agent: AgentProfile) -> float:
        """评估智能体可信度 (基于 reliability_score)."""
        return agent.reliability_score
