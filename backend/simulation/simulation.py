"""执行引擎 - 模拟任务执行."""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Optional

from backend.core.models import (
    ExecutionPlan,
    TaskResult,
    TaskStatus,
)
from backend.registry.agent_registry import AgentRegistry


class SimulationExecutor:
    """仿真执行器.

    模拟TACN任务执行，支持确定性和随机性仿真.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        stochastic: bool = True,
        failure_rate: float = 0.05,
        seed: Optional[int] = None,
    ):
        self.registry = registry
        self.stochastic = stochastic
        self.failure_rate = failure_rate
        if seed is not None:
            random.seed(seed)

    def execute(self, plan: ExecutionPlan) -> TaskResult:
        """执行计划.

        Args:
            plan: 执行计划

        Returns:
            任务执行结果
        """
        start_time = time.time()

        # 模拟子任务执行
        subtask_results: dict[str, dict] = {}
        actual_latencies: dict[str, float] = {}
        agent_utilization: dict[str, float] = {}
        all_success = True

        # 按拓扑顺序执行
        execution_order = self._get_execution_order(plan)

        for subtask_id in execution_order:
            assignment = self._find_assignment(plan.assignments, subtask_id)
            if assignment is None:
                subtask_results[subtask_id] = {
                    "status": "skipped",
                    "reason": "no_assignment",
                }
                continue

            # 模拟执行
            result = self._simulate_subtask_execution(assignment)
            subtask_results[subtask_id] = result

            # 跟踪延迟
            actual_latencies[subtask_id] = result.get("actual_latency_ms", 0)

            # 跟踪智能体利用率
            agent_id = assignment.agent_id
            if agent_id not in agent_utilization:
                agent_utilization[agent_id] = 0.0
            agent_utilization[agent_id] += result.get("actual_latency_ms", 0)

            if not result.get("success", False):
                all_success = False

        # 计算总指标
        total_latency = sum(actual_latencies.values())
        total_cost = sum(a.estimated_cost for a in plan.assignments)

        # 归一化利用率
        max_util = max(agent_utilization.values()) if agent_utilization else 1.0
        for agent_id in agent_utilization:
            agent_utilization[agent_id] /= max_util

        # 确定最终状态
        if all_success:
            status = TaskStatus.COMPLETED
        elif any(r.get("status") == "timeout" for r in subtask_results.values()):
            status = TaskStatus.TIMEOUT
        else:
            status = TaskStatus.FAILED

        # 检查截止时间
        deadline = plan.intent.deadline_ms
        if deadline and total_latency > deadline:
            status = TaskStatus.TIMEOUT

        return TaskResult(
            task_id=plan.task_id,
            plan_id=plan.id,
            status=status,
            actual_latency_ms=total_latency,
            actual_cost=total_cost,
            success=all_success,
            output={
                "subtask_results": subtask_results,
                "execution_order": execution_order,
            },
            error=None if all_success else "One or more subtasks failed",
            subtask_results=subtask_results,
            agent_utilization=agent_utilization,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            metadata={
                "simulation_mode": "stochastic" if self.stochastic else "deterministic",
                "failure_rate": self.failure_rate,
            },
        )

    def _simulate_subtask_execution(self, assignment) -> dict:
        """模拟单个子任务执行."""
        agent = self.registry.get_agent(assignment.agent_id)
        if agent is None:
            return {
                "status": "failed",
                "reason": "agent_not_found",
                "success": False,
                "actual_latency_ms": 0,
            }

        base_latency = assignment.estimated_duration_ms

        if self.stochastic:
            latency_factor = random.uniform(0.8, 1.2)
            actual_latency = base_latency * latency_factor

            if random.random() < self.failure_rate:
                return {
                    "status": "failed",
                    "reason": "random_failure",
                    "success": False,
                    "actual_latency_ms": actual_latency * 0.5,
                }
        else:
            actual_latency = base_latency

        return {
            "status": "completed",
            "success": True,
            "actual_latency_ms": actual_latency,
            "agent_id": assignment.agent_id,
            "agent_location": assignment.location.value,
        }

    def _get_execution_order(self, plan: ExecutionPlan) -> list[str]:
        """获取执行顺序."""
        if plan.parallel_groups:
            order = []
            for group in plan.parallel_groups:
                order.extend(group)
            return order

        graph = plan.subtask_graph
        in_degree = {st.id: 0 for st in graph.subtasks}

        for edge in graph.edges:
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        queue = [st.id for st in graph.subtasks if in_degree[st] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for edge in graph.edges:
                if edge.source_id == node:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append(edge.target_id)

        return result

    def _find_assignment(self, assignments, subtask_id: str):
        """查找子任务的分配."""
        for assignment in assignments:
            if assignment.subtask_id == subtask_id:
                return assignment
        return None

    def execute_batch(self, plans: list[ExecutionPlan]) -> list[TaskResult]:
        """批量执行计划."""
        return [self.execute(plan) for plan in plans]

    def get_simulation_statistics(self, results: list[TaskResult]) -> dict:
        """获取仿真统计信息."""
        if not results:
            return {
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "avg_cost": 0.0,
            }

        successful = sum(1 for r in results if r.success)
        total_latency = sum(r.actual_latency_ms for r in results)
        total_cost = sum(r.actual_cost for r in results)

        latencies = [r.actual_latency_ms for r in results]
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        return {
            "total_tasks": len(results),
            "successful_tasks": successful,
            "success_rate": successful / len(results),
            "avg_latency_ms": total_latency / len(results),
            "p95_latency_ms": p95_latency,
            "avg_cost": total_cost / len(results),
            "total_cost": total_cost,
            "status_counts": self._count_statuses(results),
        }

    def _count_statuses(self, results: list[TaskResult]) -> dict[str, int]:
        """统计状态数量."""
        counts: dict[str, int] = {}
        for result in results:
            status = result.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts
