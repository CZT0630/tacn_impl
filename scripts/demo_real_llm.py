"""TACN 端到端 Demo — 真实 LLM 驱动.

验证完整流水线:
  用户请求 → 意图解析(LLM) → 子任务分解(LLM) → MTCC路由 → Agent ReAct执行 → 结果汇总

用法:
  python scripts/demo_real_llm.py                    # 单场景
  python scripts/demo_real_llm.py --all              # 全部场景
  python scripts/demo_real_llm.py --scenario fire    # 指定场景
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.models import TaskStatus
from backend.llm.config import LLMConfig
from backend.orchestration.tacn_system import TACNSystem
from backend.registry.agent_registry import create_default_registry
from backend.registry.model_registry import create_default_model_registry
from backend.registry.tool_registry import create_default_tool_registry
from backend.registry.context_registry import create_default_context_registry
from backend.infrastructure.network import NetworkModel


# ============================================================================
# 测试场景
# ============================================================================

SCENARIOS = {
    "fire": {
        "name": "🔥 火灾应急响应",
        "request": "实验楼3层烟雾传感器检测到浓度异常升高，温度也在快速上升，请立即判断是否需要触发消防告警并通知相关人员",
        "expect_intent": "emergency_response",
    },
    "inspection": {
        "name": "🔍 设备巡检",
        "request": "请对A区的空调机组和配电柜进行全面巡检，检查温度是否异常，并检索上次维护记录",
        "expect_intent": "robot_inspection",
    },
    "security": {
        "name": "🛡️ 安防监控",
        "request": "东门摄像头检测到一名未佩戴工牌的人员在非工作时间进入园区，请分析行为并通知安保",
        "expect_intent": "security_monitoring",
    },
    "maintenance": {
        "name": "🔧 预测性维护",
        "request": "B区冷却塔近3天振动数据持续上升，请分析趋势并预测是否需要提前维护",
        "expect_intent": "predictive_maintenance",
    },
    "meeting": {
        "name": "📋 会议助手",
        "request": "明天下午2点在3楼会议室开项目评审会，请帮我检查日程冲突、预订会议室并通知所有参会人",
        "expect_intent": "meeting_assistant",
    },
}


# ============================================================================
# 可视化输出
# ============================================================================

def print_header(title: str):
    width = 70
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


def print_step(step: str, detail: str = ""):
    print(f"\n  ▶ {step}")
    if detail:
        for line in detail.split("\n"):
            print(f"    {line}")


def print_plan(plan):
    """可视化执行计划."""
    print_step("意图解析结果",
        f"意图类型: {plan.intent.intent_type.value}\n"
        f"隐私级别: {plan.intent.privacy_level.value}\n"
        f"需要协作: {plan.intent.requires_collaboration}\n"
        f"截止时间: {plan.intent.deadline_ms}ms\n"
        f"所需能力: {[c.capability_type.value for c in plan.intent.required_capabilities]}"
    )

    print_step("子任务分解 (DAG)",
        f"子任务数: {len(plan.subtask_graph.subtasks)}\n"
        f"依赖边数: {len(plan.subtask_graph.edges)}\n"
        f"并行组数: {len(plan.parallel_groups)}"
    )

    assignment_map = {a.subtask_id: a for a in plan.assignments}
    for i, group in enumerate(plan.parallel_groups):
        group_info = []
        for st_id in group:
            st = plan.subtask_graph.get_subtask(st_id)
            a = assignment_map.get(st_id)
            if st and a:
                group_info.append(f"{st.name} → Agent({a.location.value})")
        print(f"    Stage {i+1} (可并行): {', '.join(group_info)}")

    print_step("MTCC 路由决策",
        f"路由模式: {plan.metadata.get('routing_mode', 'unknown')}\n"
        f"预估延迟: {plan.estimated_total_latency_ms:.0f}ms\n"
        f"预估成本: ${plan.estimated_total_cost:.4f}\n"
        f"关键路径: {' → '.join(plan.critical_path[:5])}"
    )


def print_result(result):
    """可视化执行结果."""
    status_icon = {
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.TIMEOUT: "⏰",
    }.get(result.status, "❓")

    print_step("执行结果",
        f"状态: {status_icon} {result.status.value}\n"
        f"实际延迟: {result.actual_latency_ms:.0f}ms\n"
        f"实际成本: ${result.actual_cost:.4f}"
    )

    # 子任务结果
    for st_id, sr in result.subtask_results.items():
        if not isinstance(sr, dict):
            continue
        icon = "✅" if sr.get("success") else "❌"
        agent_name = sr.get("agent_name", sr.get("agent_id", "?"))
        agent_type = sr.get("agent_type", "?")
        location = sr.get("agent_location", "?")
        output = sr.get("output", "")
        error = sr.get("error")

        print(f"    {icon} [{agent_type}@{location}] {agent_name}")
        if output:
            # 截断过长的输出
            output_str = str(output)
            if len(output_str) > 300:
                output_str = output_str[:300] + "..."
            print(f"       输出: {output_str}")
        if error:
            print(f"       错误: {error}")


# ============================================================================
# 单场景运行
# ============================================================================

async def run_scenario(system: TACNSystem, scenario_key: str, scenario: dict) -> dict:
    """运行单个测试场景."""
    print_header(f"{scenario['name']}  ({scenario_key})")
    print(f"\n  用户请求: {scenario['request']}")

    # 1. 意图解析 + 子任务分解 + 路由
    t0 = time.time()
    plan = await system.process_request(scenario["request"])
    plan_ms = (time.time() - t0) * 1000
    print_plan(plan)
    print(f"\n    [规划耗时: {plan_ms:.0f}ms]")

    # 2. 执行计划
    t1 = time.time()
    result = await system.execute_plan(plan)
    exec_ms = (time.time() - t1) * 1000
    print_result(result)
    print(f"\n    [执行耗时: {exec_ms:.0f}ms]")

    # 3. 验证
    intent_correct = plan.intent.intent_type.value == scenario["expect_intent"]
    print(f"\n  🎯 意图分类: {'✅ 正确' if intent_correct else '❌ 偏差'} "
          f"(期望={scenario['expect_intent']}, 实际={plan.intent.intent_type.value})")

    return {
        "scenario": scenario_key,
        "intent_type": plan.intent.intent_type.value,
        "intent_correct": intent_correct,
        "num_subtasks": len(plan.subtask_graph.subtasks),
        "num_assignments": len(plan.assignments),
        "routing_mode": plan.metadata.get("routing_mode"),
        "plan_latency_ms": plan_ms,
        "exec_latency_ms": exec_ms,
        "total_latency_ms": plan_ms + exec_ms,
        "result_status": result.status.value,
        "success": result.success,
        "actual_cost": result.actual_cost,
    }


# ============================================================================
# 主入口
# ============================================================================

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="TACN 端到端 Demo (真实 LLM)")
    parser.add_argument("--scenario", "-s", choices=list(SCENARIOS.keys()), help="指定场景")
    parser.add_argument("--all", "-a", action="store_true", help="运行全部场景")
    parser.add_argument("--no-mtcc", action="store_true", help="使用简单路由而非MTCC")
    args = parser.parse_args()

    print_header("TACN 端到端 Demo — 真实 LLM 驱动")
    print(f"\n  LLM: mimo-v2.5 @ xiaomimimo.com")
    print(f"  模式: {'简单路由' if args.no_mtcc else 'MTCC 编排'}")

    # 初始化系统
    registry = create_default_registry()
    llm_config = LLMConfig()

    kwargs = {"registry": registry, "llm_config": llm_config}
    if not args.no_mtcc:
        kwargs.update({
            "model_registry": create_default_model_registry(),
            "tool_registry": create_default_tool_registry(),
            "context_registry": create_default_context_registry(),
            "network_model": NetworkModel(),
        })

    system = TACNSystem(**kwargs)

    print(f"\n  已注册 Agent: {len(registry.get_all_agents())}")
    for loc in ["terminal", "peer", "edge", "cloud"]:
        agents = registry.get_agents_by_location(
            __import__("backend.core.models", fromlist=["Location"]).Location(loc)
        )
        names = [a.name for a in agents]
        print(f"    {loc}: {names}")

    # 运行场景
    if args.all:
        results = []
        for key, scenario in SCENARIOS.items():
            r = await run_scenario(system, key, scenario)
            results.append(r)
    elif args.scenario:
        results = [await run_scenario(system, args.scenario, SCENARIOS[args.scenario])]
    else:
        # 默认运行火灾场景
        results = [await run_scenario(system, "fire", SCENARIOS["fire"])]

    # 汇总
    print_header("📊 汇总统计")
    success_count = sum(1 for r in results if r["success"])
    intent_correct_count = sum(1 for r in results if r["intent_correct"])
    total_latency = sum(r["total_latency_ms"] for r in results)

    print(f"\n  场景数: {len(results)}")
    print(f"  执行成功: {success_count}/{len(results)}")
    print(f"  意图正确: {intent_correct_count}/{len(results)}")
    print(f"  总耗时: {total_latency:.0f}ms")
    print(f"  平均耗时: {total_latency/len(results):.0f}ms/场景")

    for r in results:
        icon = "✅" if r["success"] else "❌"
        print(f"    {icon} {r['scenario']}: {r['intent_type']} | "
              f"{r['num_subtasks']}子任务 | {r['total_latency_ms']:.0f}ms")

    # 保存结果
    output_path = Path("outputs/demo/real_llm_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
