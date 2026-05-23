"""TACN系统 - 协调整个TACN流水线."""

from __future__ import annotations

import time
from typing import Any, Optional

from backend.core.models import (
    AgentAssignment,
    ExecutionPlan,
    Intent,
    Location,
    SubTaskGraph,
    SubTaskResult,
    TaskResult,
    TaskStatus,
)
from backend.llm import LLMClient, LLMConfig, create_llm_client
from backend.parser.intent_parser import LLMIntentParser
from backend.parser.subtask_builder import LLMSubTaskBuilder
from backend.registry.agent_registry import AgentRegistry
from backend.router.capability_router import AgentCapabilityRouter, RoutingConfig
from backend.agent.factory import AgentManager


class TACNSystem:
    """TACN系统 - 串联整个流水线.

    流程: 请求 → 意图解析(LLM) → 子任务分解(LLM) → 能力路由(算法) → 执行 → 汇总

    支持两种 LLM 接入方式:
    - llm_config: LLMConfig 对象（推荐）
    - llm_client: 直接传入 LLMClient 实例（向后兼容）
    """

    def __init__(
        self,
        registry: AgentRegistry,
        llm_client: LLMClient | None = None,
        llm_config: LLMConfig | None = None,
        routing_config: Optional[RoutingConfig] = None,
    ):
        self.registry = registry

        # 解析 LLM 客户端: 优先用 llm_client，否则用 llm_config 创建
        if llm_client is not None:
            resolved_client = llm_client
        elif llm_config is not None:
            resolved_client = create_llm_client(llm_config)
        else:
            resolved_client = None

        self.intent_parser = LLMIntentParser(resolved_client)
        self.subtask_builder = LLMSubTaskBuilder(resolved_client)
        self.router = AgentCapabilityRouter(registry, routing_config)
        self.agent_manager = AgentManager(registry, resolved_client)
        self.agent_manager.initialize()

    async def process_request(
        self,
        request: str,
        deadline_ms: Optional[float] = None,
    ) -> ExecutionPlan:
        """处理用户请求 → 生成执行计划.

        Args:
            request: 自然语言请求
            deadline_ms: 截止时间(毫秒)

        Returns:
            执行计划
        """
        start_time = time.time()

        # 1. LLM解析意图
        intent = await self.intent_parser.parse(request, deadline_ms)

        # 2. LLM分解子任务图
        subtask_graph = await self.subtask_builder.build(intent)

        # 3. 计算关键路径
        critical_path = self.subtask_builder.get_critical_path(subtask_graph)

        # 4. 算法路由: 子任务 → Agent
        assignments = self.router.route_subtask_graph(subtask_graph)

        # 5. 计算并行组
        parallel_groups = self._calculate_parallel_groups(subtask_graph)

        # 6. 汇总指标
        total_latency = sum(a.estimated_duration_ms for a in assignments)
        total_cost = sum(a.estimated_cost for a in assignments)

        plan = ExecutionPlan(
            task_id=intent.id,
            intent=intent,
            subtask_graph=subtask_graph,
            assignments=assignments,
            estimated_total_latency_ms=total_latency,
            estimated_total_cost=total_cost,
            critical_path=critical_path,
            parallel_groups=parallel_groups,
            metadata={
                "creation_time_ms": (time.time() - start_time) * 1000,
                "num_subtasks": len(subtask_graph.subtasks),
                "num_assignments": len(assignments),
            },
        )

        return plan

    async def execute_plan(self, plan: ExecutionPlan) -> TaskResult:
        """执行计划: 分发子任务 → Agent执行 → 收集结果.

        Args:
            plan: 执行计划

        Returns:
            任务执行结果
        """
        start_time = time.time()
        results: list[SubTaskResult] = []

        # 按拓扑顺序执行
        execution_order = self._get_execution_order(plan)

        for subtask_id in execution_order:
            assignment = self._find_assignment(plan.assignments, subtask_id)
            if assignment is None:
                continue

            subtask = plan.subtask_graph.get_subtask(subtask_id)
            if subtask is None:
                continue

            # Agent执行子任务
            result = await self.agent_manager.execute_subtask(
                assignment.agent_id, subtask
            )
            results.append(result)

        # 汇总结果
        total_latency = sum(r.latency_ms for r in results)
        total_cost = sum(r.cost for r in results)
        all_success = all(r.success for r in results)

        # 检查截止时间
        status = TaskStatus.COMPLETED
        if not all_success:
            status = TaskStatus.FAILED
        if plan.intent.deadline_ms and total_latency > plan.intent.deadline_ms:
            status = TaskStatus.TIMEOUT

        return TaskResult(
            task_id=plan.task_id,
            plan_id=plan.id,
            status=status,
            actual_latency_ms=total_latency,
            actual_cost=total_cost,
            success=all_success,
            output={
                "results": [r.model_dump() for r in results],
            },
            subtask_results={
                r.subtask_id: {
                    "agent_id": r.agent_id,
                    "agent_location": r.location.value,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "output": r.output,
                }
                for r in results
            },
            started_at=time.time(),
            completed_at=time.time(),
        )

    def _calculate_parallel_groups(self, graph: SubTaskGraph) -> list[list[str]]:
        """计算并行执行组."""
        if not graph.subtasks:
            return []

        in_degree = {st.id: 0 for st in graph.subtasks}
        for edge in graph.edges:
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        levels = {}
        queue = [(st.id, 0) for st in graph.subtasks if in_degree[st.id] == 0]

        while queue:
            node, level = queue.pop(0)
            levels[node] = level
            for edge in graph.edges:
                if edge.source_id == node:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append((edge.target_id, level + 1))

        level_groups = {}
        for subtask_id, level in levels.items():
            level_groups.setdefault(level, []).append(subtask_id)

        return [group for _, group in sorted(level_groups.items())]

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

        queue = [st.id for st in graph.subtasks if in_degree[st.id] == 0]
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
        for a in assignments:
            if a.subtask_id == subtask_id:
                return a
        return None
