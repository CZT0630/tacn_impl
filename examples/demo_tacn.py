"""TACN完整流程演示 - 展示意图解析→子任务分解→能力路由→执行."""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.registry.agent_registry import create_default_registry
from backend.orchestration.tacn_system import TACNSystem


async def main():
    print("=" * 80)
    print("TACN - Terminal Agent Computing Network 完整流程演示")
    print("=" * 80)

    # 创建注册表和TACN系统
    registry = create_default_registry()
    tacn = TACNSystem(registry)

    # 显示系统中的Agent
    print("\n[1] TACN系统中的Agent:")
    agents = registry.get_all_agents()
    for agent in agents:
        caps = [c.capability_type.value for c in agent.capabilities]
        print(f"  {agent.name:25s} [{agent.location.value:8s}] 能力: {caps}")

    # 测试请求
    requests = [
        "实验楼烟雾传感器报警，请结合摄像头画面判断是否触发消防告警",
        "巡检机器人发现设备温度异常，请检查维护记录并给出维护建议",
        "多个摄像头检测到异常行为，请分析并通知安保人员",
    ]

    for i, request in enumerate(requests, 1):
        print(f"\n{'=' * 80}")
        print(f"[{i+1}] 用户请求: {request}")
        print("=" * 80)

        # 1. 处理请求 (意图解析 + 子任务分解 + 能力路由)
        print("\n--- Step 1: TACN处理请求 ---")
        plan = await tacn.process_request(request)

        print(f"  意图类型: {plan.intent.intent_type.value}")
        print(f"  所需能力: {[c.capability_type.value for c in plan.intent.required_capabilities]}")
        print(f"  隐私级别: {plan.intent.privacy_level.value}")
        print(f"  截止时间: {plan.intent.deadline_ms}ms")

        print(f"\n  子任务图 ({len(plan.subtask_graph.subtasks)}个子任务, {len(plan.subtask_graph.edges)}条依赖):")
        for j, st in enumerate(plan.subtask_graph.subtasks, 1):
            caps = [c.capability_type.value for c in st.required_capabilities]
            print(f"    {j}. {st.name:25s} 能力: {caps}")

        print(f"\n  依赖关系:")
        for edge in plan.subtask_graph.edges:
            src = plan.subtask_graph.get_subtask(edge.source_id)
            tgt = plan.subtask_graph.get_subtask(edge.target_id)
            if src and tgt:
                print(f"    {src.name} -> {tgt.name}")

        print(f"\n  路由分配:")
        for a in plan.assignments:
            st = plan.subtask_graph.get_subtask(a.subtask_id)
            print(f"    {st.name if st else a.subtask_id:25s} -> {a.agent_id} [{a.location.value}] "
                  f"(延迟:{a.estimated_duration_ms:.0f}ms, 成本:${a.estimated_cost:.4f})")

        print(f"\n  预估总延迟: {plan.estimated_total_latency_ms:.0f}ms")
        print(f"  预估总成本: ${plan.estimated_total_cost:.4f}")

        # 2. 执行计划
        print("\n--- Step 2: 执行计划 ---")
        result = await tacn.execute_plan(plan)

        print(f"  执行状态: {result.status.value}")
        print(f"  实际延迟: {result.actual_latency_ms:.1f}ms")
        print(f"  实际成本: ${result.actual_cost:.4f}")
        print(f"  是否成功: {result.success}")

        print(f"\n  子任务执行结果:")
        for st_id, sr in result.subtask_results.items():
            st = plan.subtask_graph.get_subtask(st_id)
            status = "[OK]" if sr.get("success") else "[FAIL]"
            print(f"    {status} {st.name if st else st_id:25s} "
                  f"Agent: {sr.get('agent_id', 'N/A')} [{sr.get('agent_location', 'N/A')}] "
                  f"延迟: {sr.get('latency_ms', 0):.1f}ms")

    # 演示Agent通信
    print(f"\n{'=' * 80}")
    print("[4] Agent通信演示")
    print("=" * 80)

    agents_dict = tacn.agent_manager.factory.get_all_agents()
    terminal = None
    edge = None
    for agent in agents_dict.values():
        if agent.location.value == "terminal" and terminal is None:
            terminal = agent
        elif agent.location.value == "edge" and edge is None:
            edge = agent

    if terminal and terminal.communicator and edge and edge.communicator:
        from backend.agent.message import Message

        received = []
        def on_msg(msg: Message):
            received.append(msg)

        terminal.communicator.subscribe("data_request", on_msg)

        print(f"\n  {edge.name} -> {terminal.name}: 请求传感器数据")
        edge.communicator.send(
            receiver_id=terminal.id,
            topic="data_request",
            payload={"type": "sensor_query", "data": "temperature"},
        )
        print(f"  消息已发送, 收到 {len(received)} 条回复")

    print(f"\n{'=' * 80}")
    print("演示完成!")
    print("=" * 80)
    print("\nTACN系统架构:")
    print("  用户请求 → TACN系统")
    print("    1. LLM意图解析 → 结构化Intent")
    print("    2. LLM子任务分解 → 子任务DAG")
    print("    3. 查询Agent Card → 能力匹配")
    print("    4. 多准则路由算法 → 分配Agent")
    print("    5. Agent执行(LLM+工具) → 子任务结果")
    print("    6. 结果汇总 → 返回用户")


if __name__ == "__main__":
    asyncio.run(main())
