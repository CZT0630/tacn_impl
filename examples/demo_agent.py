"""TACN Agent演示 - 展示真正的Agent执行."""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.registry.agent_registry import create_default_registry
from backend.orchestration.engine import OrchestrationEngine
from backend.agent.factory import AgentManager


async def demo_agent_execution():
    """演示Agent执行."""
    print("=" * 80)
    print("TACN Agent执行演示")
    print("=" * 80)

    # 创建注册表
    registry = create_default_registry()

    # 创建编排引擎
    engine = OrchestrationEngine(registry)

    # 创建Agent管理器
    agent_manager = AgentManager(registry)
    agent_manager.initialize()

    # 测试请求
    request = "实验楼烟雾传感器报警，请结合摄像头画面判断是否触发消防告警"

    print(f"\n输入请求: {request}\n")

    # 1. 处理请求，生成执行计划
    plan = await engine.process_request(request)

    print("执行计划:")
    print(f"  任务ID: {plan.task_id}")
    print(f"  意图类型: {plan.intent.intent_type.value}")
    print(f"  子任务数: {len(plan.subtask_graph.subtasks)}")
    print(f"  分配数: {len(plan.assignments)}")
    print(f"  预估延迟: {plan.estimated_total_latency_ms:.1f} ms")
    print(f"  预估成本: ${plan.estimated_total_cost:.4f}")

    print("\n子任务分配:")
    for i, assignment in enumerate(plan.assignments, 1):
        subtask = plan.subtask_graph.get_subtask(assignment.subtask_id)
        agent = registry.get_agent(assignment.agent_id)
        print(f"  {i}. {subtask.name if subtask else 'Unknown'}")
        print(f"     -> {agent.name if agent else 'Unknown'} ({assignment.location.value})")

    # 2. 使用Agent执行计划
    print("\n" + "-" * 40)
    print("开始Agent执行...")
    print("-" * 40)

    execution_result = agent_manager.execute_plan(plan)

    print(f"\n执行状态: {execution_result['status']}")
    print(f"总延迟: {execution_result['total_latency_ms']:.1f} ms")
    print(f"总成本: ${execution_result['total_cost']:.4f}")

    # 显示每个子任务的执行结果
    print("\n子任务执行结果:")
    for subtask_id, result in execution_result['results'].items():
        subtask = plan.subtask_graph.get_subtask(subtask_id)
        status = "[OK]" if result.get('success', False) else "[FAIL]"
        print(f"  {status} {subtask.name if subtask else subtask_id}")
        if result.get('success', False):
            print(f"    Agent: {result.get('agent_name', 'Unknown')}")
            print(f"    位置: {result.get('location', 'Unknown')}")
            if 'output' in result:
                output = result['output']
                if isinstance(output, dict):
                    for key, value in output.items():
                        if isinstance(value, dict) and 'status' in value:
                            print(f"    {key}: {value['status']}")
        else:
            print(f"    错误: {result.get('error', 'Unknown error')}")

    # 3. 显示Agent统计信息
    print("\n" + "-" * 40)
    print("Agent统计信息")
    print("-" * 40)

    agent_stats = agent_manager.get_agent_stats()
    for agent_id, stats in agent_stats.items():
        print(f"\n{stats['name']} ({stats['location']}):")
        print(f"  能力: {', '.join(stats['capabilities'])}")
        print(f"  工具: {', '.join(stats['tools']) if stats['tools'] else 'None'}")

    return execution_result


async def main():
    """主函数."""
    print("TACN - Terminal Agent Computing Network Agent演示\n")

    result = await demo_agent_execution()

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)
    print("\n每个Agent现在可以:")
    print("  1. 接收子任务")
    print("  2. 思考：分析任务需求")
    print("  3. 行动：调用工具执行操作")
    print("  4. 观察：评估执行结果")
    print("\nAgent已集成:")
    print("  - 摄像头工具 (CameraTool)")
    print("  - 传感器工具 (SensorTool)")
    print("  - 文档检索工具 (DocumentStoreTool)")
    print("  - 通知工具 (NotificationTool)")
    print("  - LLM推理工具 (LLMTool)")
    print("  - 向量数据库工具 (VectorDatabaseTool)")


if __name__ == "__main__":
    asyncio.run(main())
