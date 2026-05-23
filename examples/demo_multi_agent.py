"""TACN多层级Agent演示 - 展示不同层级的Agent."""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.registry.agent_registry import create_default_registry
from backend.orchestration.engine import OrchestrationEngine
from backend.agent.factory import AgentManager
from backend.agent.terminal_agent import TerminalAgent
from backend.agent.peer_agent import PeerAgent
from backend.agent.edge_agent import EdgeAgent
from backend.agent.cloud_agent import CloudAgent


async def demo_multi_agent():
    """演示多层级Agent."""
    print("=" * 80)
    print("TACN 多层级Agent演示")
    print("=" * 80)

    # 创建注册表
    registry = create_default_registry()

    # 创建编排引擎
    engine = OrchestrationEngine(registry)

    # 创建Agent管理器
    agent_manager = AgentManager(registry)
    agent_manager.initialize()

    # 显示系统拓扑
    print("\n系统拓扑:")
    topology = agent_manager.get_system_topology()
    for location, agents in topology.items():
        if agents:
            print(f"\n  {location.upper()}层 ({len(agents)}个Agent):")
            for agent_info in agents:
                print(f"    - {agent_info['name']} ({agent_info['type']})")

    # 测试请求
    request = "实验楼烟雾传感器报警，请结合摄像头画面判断是否触发消防告警"

    print(f"\n\n输入请求: {request}")

    # 处理请求
    plan = await engine.process_request(request)

    print("\n执行计划:")
    print(f"  任务ID: {plan.task_id}")
    print(f"  意图类型: {plan.intent.intent_type.value}")
    print(f"  子任务数: {len(plan.subtask_graph.subtasks)}")
    print(f"  分配数: {len(plan.assignments)}")

    # 显示每个子任务的分配
    print("\n子任务分配详情:")
    for i, assignment in enumerate(plan.assignments, 1):
        subtask = plan.subtask_graph.get_subtask(assignment.subtask_id)
        agent = registry.get_agent(assignment.agent_id)
        agent_obj = agent_manager.factory.get_agent(assignment.agent_id)
        agent_type = type(agent_obj).__name__ if agent_obj else "Unknown"

        print(f"\n  {i}. {subtask.name if subtask else 'Unknown'}")
        print(f"     Agent: {agent.name if agent else 'Unknown'}")
        print(f"     类型: {agent_type}")
        print(f"     位置: {assignment.location.value}")
        print(f"     能力: {', '.join([c.capability_type.value for c in (agent.capabilities if agent else [])])}")

    # 执行计划
    print("\n" + "-" * 40)
    print("开始执行...")
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
        agent_type = result.get('agent_type', 'unknown')
        print(f"\n  {status} {subtask.name if subtask else subtask_id}")
        print(f"    Agent类型: {agent_type}")
        print(f"    位置: {result.get('location', 'Unknown')}")

        if result.get('success', False):
            # 显示Agent特有信息
            if agent_type == 'terminal':
                print(f"    隐私过滤: {result.get('privacy_filtered', False)}")
                print(f"    本地执行: {result.get('local_execution', False)}")
            elif agent_type == 'peer':
                print(f"    协作终端数: {result.get('peers_connected', 0)}")
                print(f"    数据融合: {result.get('peer_collaboration', False)}")
            elif agent_type == 'edge':
                print(f"    边缘处理: {result.get('edge_processing', False)}")
                print(f"    缓存命中: {result.get('cache_hit', False)}")
                print(f"    协调终端: {result.get('terminals_coordinated', 0)}")
            elif agent_type == 'cloud':
                print(f"    全局上下文: {result.get('global_context_used', False)}")
                print(f"    跨区域整合: {result.get('cross_region_integrated', False)}")
        else:
            print(f"    错误: {result.get('error', 'Unknown error')}")

    return execution_result


async def main():
    """主函数."""
    print("TACN - Terminal Agent Computing Network 多层级Agent演示\n")

    result = await demo_multi_agent()

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)
    print("\nTACN Agent层级结构:")
    print("  1. Terminal Agent - 终端智能体")
    print("     - 离数据源最近，低延迟")
    print("     - 隐私友好，本地处理")
    print("     - 资源受限，轻量级推理")
    print("")
    print("  2. Peer Agent - 对等智能体")
    print("     - 多终端协作")
    print("     - D2D通信")
    print("     - 多源数据融合")
    print("")
    print("  3. Edge Agent - 边缘智能体")
    print("     - 比终端更强算力")
    print("     - 比云端更接近现场")
    print("     - 协调多个终端")
    print("     - GPU加速处理")
    print("")
    print("  4. Cloud Agent - 云端智能体")
    print("     - 最强模型能力")
    print("     - 全局上下文管理")
    print("     - 跨区域知识整合")
    print("     - 复杂推理和规划")


if __name__ == "__main__":
    asyncio.run(main())
