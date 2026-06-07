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
from backend.agent.runtime import AgentRuntime


class TACNSystem:
    """TACN系统 - 串联整个流水线.

    流程: 请求 → 意图解析(LLM) → 子任务分解(LLM) → 能力路由(算法) → 执行 → 汇总

    支持两种路由模式:
    - MTCC 模式: 传入 model_registry + tool_registry + context_registry + network_model
    - 简单模式: 仅使用 capability_router（向后兼容）

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
        # MTCC 参数
        model_registry=None,
        tool_registry=None,
        context_registry=None,
        network_model=None,
        mtcc_config=None,
        # AgentRuntime
        runtime: Optional[AgentRuntime] = None,
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

        # MTCC 模式判断
        self.use_mtcc = all(
            x is not None
            for x in [model_registry, tool_registry, context_registry, network_model]
        )

        if self.use_mtcc:
            from backend.orchestration.mtcc_orchestrator import (
                MTCCConfig,
                MTCCOrchestrator,
            )
            from backend.control_planes.resource_control import ResourceControlPlane
            from backend.control_planes.semantic_control import SemanticControlPlane
            from backend.control_planes.trust_privacy_control import TrustPrivacyControlPlane

            cfg = mtcc_config or MTCCConfig()
            self.mtcc = MTCCOrchestrator(
                registry, model_registry, tool_registry,
                context_registry, network_model, cfg,
            )
            self.resource_control = ResourceControlPlane(network_model, None, registry)
            self.semantic_control = SemanticControlPlane(
                registry, model_registry, tool_registry, context_registry,
            )
            self.trust_control = TrustPrivacyControlPlane()
        else:
            self.router = AgentCapabilityRouter(registry, routing_config)

        # AgentRuntime 或 AgentManager
        from backend.agent.tools import create_default_tool_registry
        from backend.agent.llm_agent import HookRegistry, SkillLoader

        tool_registry = create_default_tool_registry()
        self.hooks = HookRegistry()
        self.skill_loader = SkillLoader()

        if runtime is not None:
            self.runtime = runtime
            self.agent_manager = runtime.manager if hasattr(runtime, 'manager') else None
        else:
            self.runtime = None
            self.agent_manager = AgentManager(
                registry, resolved_client,
                tool_registry=tool_registry,
                hooks=self.hooks,
                skill_loader=self.skill_loader,
            )
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

        # 4. 路由: 子任务 → Agent
        if self.use_mtcc:
            mtcc_decisions = self.mtcc.orchestrate_graph(subtask_graph)
            assignments = [self._decision_to_assignment(d) for d in mtcc_decisions]
        else:
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
                "routing_mode": "mtcc" if self.use_mtcc else "simple",
            },
        )

        return plan

    async def execute_plan(self, plan: ExecutionPlan) -> TaskResult:
        """执行计划 — 支持并行组 + 上下文传递.

        参考 LCC 的并行调度模式:
        - parallel_groups 内的子任务用 asyncio.gather 并行执行
        - 上游子任务的结果自动注入下游 agent 的上下文
        """
        import asyncio

        start_time = time.time()
        all_results: list[SubTaskResult] = []
        results_map: dict[str, dict] = {}  # subtask_id → result dict (用于上下文注入)

        if plan.parallel_groups:
            # 按并行组执行 — 同组内并行，组间串行
            for group in plan.parallel_groups:
                tasks = []
                group_items = []  # (subtask_id, assignment, subtask)

                for subtask_id in group:
                    assignment = self._find_assignment(plan.assignments, subtask_id)
                    if assignment is None:
                        continue
                    subtask = plan.subtask_graph.get_subtask(subtask_id)
                    if subtask is None:
                        continue

                    # 构建上下文: 注入上游结果
                    context = self._build_upstream_context(plan, results_map, subtask_id)
                    tasks.append(self.agent_manager.execute_subtask(assignment.agent_id, subtask, context))
                    group_items.append((subtask_id, assignment))

                if tasks:
                    group_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for (subtask_id, assignment), result in zip(group_items, group_results):
                        if isinstance(result, Exception):
                            result = SubTaskResult(
                                subtask_id=subtask_id,
                                agent_id=assignment.agent_id,
                                location=assignment.location,
                                success=False,
                                error=str(result),
                            )
                        all_results.append(result)
                        results_map[subtask_id] = {
                            "agent_id": result.agent_id,
                            "agent_location": result.location.value,
                            "success": result.success,
                            "latency_ms": result.latency_ms,
                            "output": result.output,
                            "error": result.error,
                        }
        else:
            # 无并行组 → 按拓扑序串行，但仍传递上下文
            execution_order = self._get_execution_order(plan)
            for subtask_id in execution_order:
                assignment = self._find_assignment(plan.assignments, subtask_id)
                if assignment is None:
                    continue
                subtask = plan.subtask_graph.get_subtask(subtask_id)
                if subtask is None:
                    continue

                context = self._build_upstream_context(plan, results_map, subtask_id)
                result = await self.agent_manager.execute_subtask(assignment.agent_id, subtask, context)
                all_results.append(result)
                results_map[subtask_id] = {
                    "agent_id": result.agent_id,
                    "agent_location": result.location.value,
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "output": result.output,
                    "error": result.error,
                }

        # 汇总结果
        total_latency = sum(r.latency_ms for r in all_results)
        total_cost = sum(r.cost for r in all_results)
        all_success = all(r.success for r in all_results)

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
            output={"results": [r.model_dump() for r in all_results]},
            subtask_results=results_map,
            started_at=time.time(),
            completed_at=time.time(),
        )

    def _build_upstream_context(self, plan, results_map: dict, current_subtask_id: str) -> dict:
        """构建上游上下文 — 把前驱子任务的结果注入当前 agent."""
        upstream = {}
        predecessors = plan.subtask_graph.get_predecessors(current_subtask_id)
        for pred_id in predecessors:
            if pred_id in results_map:
                upstream[pred_id] = results_map[pred_id]
        return {"upstream_results": upstream} if upstream else {}

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

    def _decision_to_assignment(self, decision) -> AgentAssignment:
        """将 MTCCDecision 转换为 AgentAssignment."""
        agent = self.registry.get_agent(decision.selected_agent_id)
        return AgentAssignment(
            subtask_id=decision.subtask_id,
            agent_id=decision.selected_agent_id,
            location=agent.location if agent else decision.selected_compute_tier,
            estimated_duration_ms=decision.estimated_latency_ms,
            estimated_cost=decision.estimated_cost,
        )
