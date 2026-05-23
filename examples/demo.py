"""TACN演示脚本 - 展示核心功能."""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.models import IntentType
from backend.registry.agent_registry import create_default_registry
from backend.orchestration.engine import OrchestrationEngine
from backend.simulation.simulation import SimulationExecutor
from backend.workload.generator import WorkloadGenerator
from backend.baselines.cloud_only import CloudOnlyBaseline
from backend.baselines.resource_aware_cpn import ResourceAwareCPN
from backend.baselines.semantic_router import SemanticOnlyRouter
from backend.evaluation.metrics import MetricsCalculator


async def demo_single_request():
    """演示单个请求处理."""
    print("=" * 80)
    print("TACN 单个请求处理演示")
    print("=" * 80)

    # 创建注册表和引擎
    registry = create_default_registry()
    engine = OrchestrationEngine(registry)

    # 测试请求
    request = "实验楼烟雾传感器报警，请结合摄像头画面、维护记录和安全规范判断是否触发消防告警并通知附近人员"

    print(f"\n输入请求: {request}\n")

    # 处理请求
    plan = await engine.process_request(request)

    # 打印执行计划
    print(engine.visualize_plan(plan))

    # 执行任务
    executor = SimulationExecutor(registry, stochastic=True, seed=42)
    result = executor.execute(plan)

    print("\n" + "=" * 40)
    print("执行结果")
    print("=" * 40)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    print(f"实际延迟: {result.actual_latency_ms:.1f} ms")
    print(f"实际成本: ${result.actual_cost:.4f}")

    return plan, result


async def demo_batch_experiment():
    """演示批量实验."""
    print("\n" + "=" * 80)
    print("TACN 批量实验演示")
    print("=" * 80)

    # 创建组件
    registry = create_default_registry()
    engine = OrchestrationEngine(registry)
    executor = SimulationExecutor(registry, stochastic=True, seed=42)
    workload_gen = WorkloadGenerator(seed=42)
    metrics_calc = MetricsCalculator()

    # 创建基线
    cloud_only = CloudOnlyBaseline(registry)
    cpn_baseline = ResourceAwareCPN(registry)
    semantic_router = SemanticOnlyRouter(registry)

    # 生成工作负载
    num_tasks = 20
    requests = workload_gen.generate_mixed(num_tasks)

    print(f"\n生成 {num_tasks} 个混合类型请求")

    # 运行各方法
    all_results = {}
    for request in requests:
        # TACN
        try:
            plan = await engine.process_request(request)
            result = executor.execute(plan)
            if "TACN" not in all_results:
                all_results["TACN"] = []
            all_results["TACN"].append(result)
        except Exception as e:
            print(f"  TACN 处理失败: {e}")

        # Cloud-only
        try:
            plan = await cloud_only.process(request)
            result = executor.execute(plan)
            if "Cloud-only" not in all_results:
                all_results["Cloud-only"] = []
            all_results["Cloud-only"].append(result)
        except Exception as e:
            print(f"  Cloud-only 处理失败: {e}")

        # CPN
        try:
            plan = await cpn_baseline.process(request)
            result = executor.execute(plan)
            if "CPN" not in all_results:
                all_results["CPN"] = []
            all_results["CPN"].append(result)
        except Exception as e:
            print(f"  CPN 处理失败: {e}")

        # Semantic
        try:
            plan = await semantic_router.process(request)
            result = executor.execute(plan)
            if "Semantic" not in all_results:
                all_results["Semantic"] = []
            all_results["Semantic"].append(result)
        except Exception as e:
            print(f"  Semantic 处理失败: {e}")

    # 计算指标
    print("\n" + "-" * 40)
    print("实验结果对比")
    print("-" * 40)

    metrics_summary = {}
    for name, results in all_results.items():
        if results:
            metrics = metrics_calc.calculate_all_metrics(results)
            metrics_summary[name] = metrics

            print(f"\n{name}:")
            print(f"  任务成功率: {metrics['task_success_rate']:.1%}")
            print(f"  P95延迟: {metrics['p95_latency_ms']:.0f} ms")
            print(f"  平均成本: ${metrics['avg_cost']:.4f}")
            print(f"  云端卸载比例: {metrics['cloud_offloading_ratio']:.1%}")

    return metrics_summary


async def demo_intents():
    """演示不同意图类型."""
    print("\n" + "=" * 80)
    print("TACN 意图类型演示")
    print("=" * 80)

    registry = create_default_registry()
    engine = OrchestrationEngine(registry)

    requests = {
        IntentType.EMERGENCY_RESPONSE: "实验楼烟雾传感器报警，请判断是否触发消防告警",
        IntentType.ROBOT_INSPECTION: "巡检机器人发现设备温度异常，请检查维护记录并给出建议",
        IntentType.SECURITY_MONITORING: "多个摄像头检测到异常行为，请分析并通知安保人员",
        IntentType.PREDICTIVE_MAINTENANCE: "根据历史数据和实时状态预测设备故障风险",
        IntentType.MEETING_ASSISTANT: "请帮我安排明天下午的技术评审会议",
    }

    for intent_type, request in requests.items():
        print(f"\n意图类型: {intent_type.value}")
        print(f"请求: {request}")

        plan = await engine.process_request(request)
        print(f"子任务数: {len(plan.subtask_graph.subtasks)}")
        print(f"分配数: {len(plan.assignments)}")
        print(f"预估延迟: {plan.estimated_total_latency_ms:.0f} ms")


async def main():
    """主演示函数."""
    print("TACN - Terminal Agent Computing Network 演示\n")

    # 运行各演示
    await demo_single_request()
    await demo_intents()
    metrics = await demo_batch_experiment()

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)
    print("\n启动Web界面请运行:")
    print("  cd backend && uvicorn main:app --reload --port 8000")
    print("  然后打开 frontend/index.html")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
