"""TACN Agent通信演示 - 展示Agent之间的消息通信."""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.registry.agent_registry import create_default_registry
from backend.agent.factory import AgentManager
from backend.agent.message import Message, MessageType, MessagePriority


async def demo_agent_communication():
    """演示Agent之间的通信."""
    print("=" * 80)
    print("TACN Agent通信演示")
    print("=" * 80)

    # 创建注册表
    registry = create_default_registry()

    # 创建Agent管理器
    agent_manager = AgentManager(registry)
    agent_manager.initialize()

    # 获取消息总线
    message_bus = agent_manager.factory.message_bus

    # 显示所有Agent
    print("\n已注册的Agent:")
    agents = agent_manager.factory.get_all_agents()
    for agent_id, agent in agents.items():
        print(f"  - {agent.name} ({agent.location.value})")
        if agent.communicator:
            print(f"    通信器: 已启用")

    # 演示1: 点对点消息
    print("\n" + "-" * 40)
    print("演示1: 点对点消息")
    print("-" * 40)

    # 获取一个终端Agent和一个边缘Agent
    terminal = None
    edge = None
    for agent in agents.values():
        if agent.location.value == "terminal" and terminal is None:
            terminal = agent
        elif agent.location.value == "edge" and edge is None:
            edge = agent

    if terminal and terminal.communicator and edge and edge.communicator:
        # 订阅消息
        received_messages = []

        def on_message(msg: Message):
            received_messages.append(msg)
            print(f"  收到消息: {msg.topic} from {msg.sender_id}")
            print(f"  内容: {msg.payload}")

        terminal.communicator.subscribe("sensor_alert", on_message)

        # 终端发送消息给边缘
        print(f"\n  {terminal.name} -> {edge.name}: 发送传感器警报")
        terminal.communicator.send(
            receiver_id=edge.id,
            topic="sensor_alert",
            payload={
                "type": "smoke_detected",
                "level": "high",
                "location": "building_A_floor_3",
            }
        )

        print(f"  消息已发送，收到 {len(received_messages)} 条消息")

    # 演示2: 广播消息
    print("\n" + "-" * 40)
    print("演示2: 广播消息")
    print("-" * 40)

    broadcast_received = []

    def on_broadcast(msg: Message):
        broadcast_received.append(msg)
        print(f"  收到广播: {msg.topic} from {msg.sender_id}")

    # 所有Agent订阅广播
    for agent in agents.values():
        if agent.communicator:
            agent.communicator.subscribe("system_broadcast", on_broadcast)

    # 云端Agent广播
    cloud_agent = None
    for agent in agents.values():
        if agent.location.value == "cloud":
            cloud_agent = agent
            break

    if cloud_agent and cloud_agent.communicator:
        print(f"\n  {cloud_agent.name} 广播: 系统更新")
        cloud_agent.communicator.broadcast(
            topic="system_broadcast",
            payload={
                "type": "policy_update",
                "policy": "safety_v2.1",
                "effective_date": "2024-01-01",
            }
        )
        print(f"  广播已发送，共收到 {len(broadcast_received)} 条消息")

    # 演示3: 请求-响应模式
    print("\n" + "-" * 40)
    print("演示3: 请求-响应模式")
    print("-" * 40)

    if terminal and terminal.communicator and edge and edge.communicator:
        print(f"\n  {terminal.name} -> {edge.name}: 请求边缘缓存数据")

        # 边缘Agent订阅并响应
        def handle_cache_request(msg: Message):
            if msg.topic == "cache_query":
                print(f"  边缘Agent处理缓存查询")
                # 发送响应
                edge.communicator.send(
                    receiver_id=msg.sender_id,
                    topic="cache_response",
                    payload={
                        "cached": True,
                        "data": {"temperature": 24.5, "humidity": 62.0},
                    },
                    reply_to=msg.id,
                )

        edge.communicator.subscribe("cache_query", handle_cache_request)

        # 终端发送请求
        response = terminal.communicator.request(
            receiver_id=edge.id,
            topic="cache_query",
            payload={"query": "latest_sensor_data"},
            timeout=3.0,
        )

        if response:
            print(f"  收到响应: {response.payload}")
        else:
            print(f"  请求超时")

    # 显示消息统计
    print("\n" + "-" * 40)
    print("消息统计")
    print("-" * 40)

    stats = message_bus.get_stats()
    print(f"  总消息数: {stats['total_messages']}")
    print(f"  订阅的主题: {stats['subscribed_topics']}")
    print(f"  订阅的Agent: {stats['subscribed_agents']}")

    # 显示消息历史
    history = message_bus.get_message_history(limit=10)
    print(f"\n  最近 {len(history)} 条消息:")
    for msg in history:
        sender = agents.get(msg.sender_id, None)
        sender_name = sender.name if sender else msg.sender_id
        print(f"    [{msg.type.value}] {sender_name}: {msg.topic}")

    return stats


async def main():
    """主函数."""
    print("TACN - Terminal Agent Computing Network Agent通信演示\n")

    await demo_agent_communication()

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)
    print("\nAgent通信机制说明:")
    print("  1. MessageBus - 消息总线")
    print("     - 管理所有Agent之间的消息传递")
    print("     - 支持点对点和广播消息")
    print("     - 支持主题订阅")
    print("")
    print("  2. AgentCommunicator - Agent通信器")
    print("     - 为每个Agent提供通信接口")
    print("     - 支持send, broadcast, request方法")
    print("     - 自动管理消息订阅")
    print("")
    print("  3. 消息类型:")
    print("     - REQUEST/RESPONSE: 请求-响应模式")
    print("     - DATA: 数据消息")
    print("     - CONTROL: 控制消息")
    print("     - HEARTBEAT: 心跳消息")
    print("     - BROADCAST: 广播消息")


if __name__ == "__main__":
    asyncio.run(main())
