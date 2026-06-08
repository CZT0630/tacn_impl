"""TACN系统 - 协调整个TACN流水线."""

from __future__ import annotations

import time
from typing import Any, Optional

from backend.core.models import (
    AgentAssignment,
    ExecutionPlan,
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

        # AgentManager
        from backend.agent.tools import create_default_tool_registry
        from backend.agent.llm_agent import HookRegistry, SkillLoader

        tool_registry = create_default_tool_registry()
        self.hooks = HookRegistry()
        self.skill_loader = SkillLoader()

        self.agent_manager = AgentManager(
            registry, resolved_client,
            tool_registry=tool_registry,
            hooks=self.hooks,
            skill_loader=self.skill_loader,
        )
        self.agent_manager.initialize()

        # 反馈闭环 — 执行后自动更新 Agent 可靠性指标
        from backend.orchestration.feedback import ExecutionFeedback
        self._feedback = ExecutionFeedback(registry)

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
        parallel_groups = subtask_graph.parallel_groups()

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
        """执行计划 — 委托给 AgentManager，汇总后触发反馈更新.

        AgentManager 负责并行调度 + 上下文传递，
        TACNSystem 负责汇总结果 + 触发 ExecutionFeedback.
        """
        raw = await self.agent_manager.execute_plan(plan)

        # 转换为 TaskResult
        all_success = raw["status"] == "completed"
        total_latency = raw["total_latency_ms"]
        total_cost = raw["total_cost"]

        status = TaskStatus.COMPLETED
        if not all_success:
            status = TaskStatus.FAILED
        if plan.intent.deadline_ms and total_latency > plan.intent.deadline_ms:
            status = TaskStatus.TIMEOUT

        task_result = TaskResult(
            task_id=plan.task_id,
            plan_id=plan.id,
            status=status,
            actual_latency_ms=total_latency,
            actual_cost=total_cost,
            success=all_success,
            output=raw,
            subtask_results=raw.get("results", {}),
            started_at=time.time(),
            completed_at=time.time(),
        )

        # 触发反馈更新（资源-能力优化环）
        if self._feedback is not None:
            self._feedback.update_after_execution(task_result, plan)

        return task_result

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
