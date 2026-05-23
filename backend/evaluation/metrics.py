"""指标计算模块 - 计算实验评估指标."""

from __future__ import annotations

from backend.core.models import TaskResult


class MetricsCalculator:
    """指标计算器.

    计算各种实验评估指标.
    """

    def calculate_task_success_rate(self, results: list[TaskResult]) -> float:
        """计算任务成功率.

        Args:
            results: 任务结果列表

        Returns:
            任务成功率 (0-1)
        """
        if not results:
            return 0.0
        successful = sum(1 for r in results if r.success)
        return successful / len(results)

    def calculate_p95_latency(self, results: list[TaskResult]) -> float:
        """计算95分位延迟.

        Args:
            results: 任务结果列表

        Returns:
            P95延迟(毫秒)
        """
        if not results:
            return 0.0
        latencies = sorted([r.actual_latency_ms for r in results])
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies) - 1)]

    def calculate_avg_latency(self, results: list[TaskResult]) -> float:
        """计算平均延迟.

        Args:
            results: 任务结果列表

        Returns:
            平均延迟(毫秒)
        """
        if not results:
            return 0.0
        total = sum(r.actual_latency_ms for r in results)
        return total / len(results)

    def calculate_total_cost(self, results: list[TaskResult]) -> float:
        """计算总成本.

        Args:
            results: 任务结果列表

        Returns:
            总成本
        """
        return sum(r.actual_cost for r in results)

    def calculate_avg_cost(self, results: list[TaskResult]) -> float:
        """计算平均成本.

        Args:
            results: 任务结果列表

        Returns:
            平均成本
        """
        if not results:
            return 0.0
        return self.calculate_total_cost(results) / len(results)

    def calculate_cloud_offloading_ratio(self, results: list[TaskResult]) -> float:
        """计算云端卸载比例.

        Args:
            results: 任务结果列表

        Returns:
            云端卸载比例 (0-1)
        """
        if not results:
            return 0.0

        cloud_count = 0
        total_assignments = 0

        for result in results:
            subtask_results = result.subtask_results
            for subtask_id, sr in subtask_results.items():
                if isinstance(sr, dict) and "agent_location" in sr:
                    total_assignments += 1
                    if sr["agent_location"] == "cloud":
                        cloud_count += 1

        return cloud_count / total_assignments if total_assignments > 0 else 0.0

    def calculate_privacy_preservation_ratio(self, results: list[TaskResult]) -> float:
        """计算隐私保护比例.

        Args:
            results: 任务结果列表

        Returns:
            隐私保护比例 (0-1)
        """
        if not results:
            return 0.0

        privacy_count = 0
        total_count = 0

        for result in results:
            subtask_results = result.subtask_results
            for subtask_id, sr in subtask_results.items():
                if isinstance(sr, dict):
                    total_count += 1
                    location = sr.get("agent_location", "")
                    # 终端和对等位置认为是隐私保护的
                    if location in ("terminal", "peer"):
                        privacy_count += 1

        return privacy_count / total_count if total_count > 0 else 0.0

    def calculate_cost_efficiency(self, results: list[TaskResult]) -> float:
        """计算成本效率（成功任务数/总成本）.

        Args:
            results: 任务结果列表

        Returns:
            成本效率
        """
        if not results:
            return 0.0

        successful = sum(1 for r in results if r.success)
        total_cost = self.calculate_total_cost(results)

        return successful / total_cost if total_cost > 0 else 0.0

    def calculate_all_metrics(self, results: list[TaskResult]) -> dict:
        """计算所有指标.

        Args:
            results: 任务结果列表

        Returns:
            指标字典
        """
        return {
            "task_success_rate": self.calculate_task_success_rate(results),
            "p95_latency_ms": self.calculate_p95_latency(results),
            "avg_latency_ms": self.calculate_avg_latency(results),
            "total_cost": self.calculate_total_cost(results),
            "avg_cost": self.calculate_avg_cost(results),
            "cloud_offloading_ratio": self.calculate_cloud_offloading_ratio(results),
            "privacy_preservation_ratio": self.calculate_privacy_preservation_ratio(results),
            "cost_efficiency": self.calculate_cost_efficiency(results),
        }
