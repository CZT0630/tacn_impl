"""编排引擎 - 协调整个TACN流水线."""

from __future__ import annotations

import time
from typing import Optional

from backend.core.models import (
    ExecutionPlan,
    Intent,
    SubTaskGraph,
)
from backend.parser.intent_parser import LLMIntentParser
from backend.parser.subtask_builder import LLMSubTaskBuilder
from backend.registry.agent_registry import AgentRegistry
from backend.router.capability_router import AgentCapabilityRouter, RoutingConfig


class OrchestrationEngine:
    """编排引擎.

    协调意图解析、子任务构建、智能体路由和执行计划生成.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        routing_config: Optional[RoutingConfig] = None,
        llm_client=None,
    ):
        self.registry = registry
        self.parser = LLMIntentParser(llm_client)
        self.builder = LLMSubTaskBuilder(llm_client)
        self.router = AgentCapabilityRouter(registry, routing_config)

    async def process_request(
        self,
        request: str,
        deadline_ms: Optional[float] = None,
    ) -> ExecutionPlan:
        """处理用户请求.

        Args:
            request: 自然语言请求
            deadline_ms: 截止时间(毫秒)

        Returns:
            执行计划
        """
        start_time = time.time()

        # 1. 解析意图
        intent = await self.parser.parse(request, deadline_ms)

        # 2. 构建子任务图
        subtask_graph = await self.builder.build(intent)

        # 3. 路由子任务到智能体
        assignments = self.router.route_subtask_graph(subtask_graph)

        # 4. 计算关键路径
        critical_path = self.builder.get_critical_path(subtask_graph)

        # 5. 计算并行组
        parallel_groups = self._calculate_parallel_groups(subtask_graph)

        # 6. 计算总指标
        total_latency = sum(a.estimated_duration_ms for a in assignments)
        total_cost = sum(a.estimated_cost for a in assignments)

        # 7. 生成执行计划
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
                "routing_stats": self.router.get_routing_statistics(assignments),
            },
        )

        return plan

    async def process_intent(self, intent: Intent) -> ExecutionPlan:
        """处理已解析的意图.

        Args:
            intent: 已解析的意图

        Returns:
            执行计划
        """
        start_time = time.time()

        # 构建子任务图
        subtask_graph = await self.builder.build(intent)

        # 路由子任务到智能体
        assignments = self.router.route_subtask_graph(subtask_graph)

        # 计算关键路径
        critical_path = self.builder.get_critical_path(subtask_graph)

        # 计算并行组
        parallel_groups = self._calculate_parallel_groups(subtask_graph)

        # 计算总指标
        total_latency = sum(a.estimated_duration_ms for a in assignments)
        total_cost = sum(a.estimated_cost for a in assignments)

        # 生成执行计划
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

    def _calculate_parallel_groups(self, graph: SubTaskGraph) -> list[list[str]]:
        """计算并行执行组."""
        if not graph.subtasks:
            return []

        levels: dict[str, int] = {}
        in_degree: dict[str, int] = {st.id: 0 for st in graph.subtasks}

        for edge in graph.edges:
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        queue = [(st.id, 0) for st in graph.subtasks if in_degree[st.id] == 0]

        while queue:
            node, level = queue.pop(0)
            levels[node] = level

            for edge in graph.edges:
                if edge.source_id == node:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append((edge.target_id, level + 1))

        level_groups: dict[int, list[str]] = {}
        for subtask_id, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(subtask_id)

        return [group for _, group in sorted(level_groups.items())]

    def visualize_plan(self, plan: ExecutionPlan) -> str:
        """生成执行计划的文本可视化."""
        lines = [
            "=" * 80,
            "TACN EXECUTION PLAN",
            "=" * 80,
            "",
            f"Task ID: {plan.task_id}",
            f"Intent Type: {plan.intent.intent_type.value}",
            f"Original Request: {plan.intent.text[:100]}...",
            "",
            "-" * 40,
            "SUBTASK GRAPH",
            "-" * 40,
        ]

        assignment_map = {a.subtask_id: a for a in plan.assignments}

        for i, subtask in enumerate(plan.subtask_graph.subtasks, 1):
            assignment = assignment_map.get(subtask.id)
            agent_info = ""
            if assignment:
                agent = self.registry.get_agent(assignment.agent_id)
                agent_info = f" -> {agent.name if agent else 'Unknown'} ({assignment.location.value})"

            lines.append(f"  {i}. {subtask.name}{agent_info}")
            lines.append(
                f"     Priority: {subtask.priority}, "
                f"Computation: {subtask.estimated_computation}, "
                f"Data: {subtask.estimated_data_size_kb}KB"
            )

        lines.extend([
            "",
            "-" * 40,
            "EXECUTION SCHEDULE",
            "-" * 40,
        ])

        if plan.parallel_groups:
            for i, group in enumerate(plan.parallel_groups):
                group_names = []
                for st_id in group:
                    st = plan.subtask_graph.get_subtask(st_id)
                    if st:
                        group_names.append(st.name)
                lines.append(f"  Stage {i + 1}: {', '.join(group_names)}")

        lines.extend([
            "",
            "-" * 40,
            "METRICS",
            "-" * 40,
            f"  Estimated Total Latency: {plan.estimated_total_latency_ms:.1f} ms",
            f"  Estimated Total Cost: ${plan.estimated_total_cost:.4f}",
            f"  Number of Subtasks: {len(plan.subtask_graph.subtasks)}",
            f"  Number of Assignments: {len(plan.assignments)}",
            f"  Critical Path Length: {len(plan.critical_path)}",
            "",
            "-" * 40,
            "AGENT UTILIZATION",
            "-" * 40,
        ])

        agent_usage: dict[str, int] = {}
        location_usage: dict[str, int] = {}
        for assignment in plan.assignments:
            agent_usage[assignment.agent_id] = agent_usage.get(assignment.agent_id, 0) + 1
            location_usage[assignment.location.value] = location_usage.get(assignment.location.value, 0) + 1

        for agent_id, count in agent_usage.items():
            agent = self.registry.get_agent(agent_id)
            name = agent.name if agent else agent_id
            lines.append(f"  {name}: {count} subtasks")

        lines.append("")
        lines.append("  By Location:")
        for loc, count in location_usage.items():
            lines.append(f"    {loc}: {count} subtasks")

        lines.append("=" * 80)

        return "\n".join(lines)
