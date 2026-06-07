"""消息系统 - Agent之间的通信机制."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class MessageType(str, Enum):
    """消息类型."""
    REQUEST = "request"           # 请求消息
    RESPONSE = "response"         # 响应消息
    DATA = "data"                 # 数据消息
    CONTROL = "control"           # 控制消息
    HEARTBEAT = "heartbeat"       # 心跳消息
    BROADCAST = "broadcast"       # 广播消息


class MessagePriority(int, Enum):
    """消息优先级."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Message:
    """消息数据结构."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.DATA
    sender_id: str = ""
    receiver_id: str = ""  # 空表示广播
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None  # 回复某条消息
    ttl: float = 30.0  # 生存时间(秒)

    def is_expired(self) -> bool:
        """检查消息是否过期."""
        return time.time() - self.timestamp > self.ttl

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "topic": self.topic,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
        }


class MessageBus:
    """消息总线 - 管理Agent之间的通信.

    支持两种模式:
    - 内存模式 (默认): 消息存在内存，进程重启丢失
    - 持久化模式: 传入 inbox_dir，消息写入 JSONL 文件 (参考 LCC)
    """

    def __init__(self, inbox_dir: str | None = None):
        self._subscribers: dict[str, list[Callable]] = {}
        self._agent_subscribers: dict[str, list[Callable]] = {}
        self._message_queue: list[Message] = []
        self._message_history: list[Message] = []
        self._max_history = 1000
        # 持久化模式
        self._inbox_dir = inbox_dir
        if inbox_dir:
            import os
            os.makedirs(inbox_dir, exist_ok=True)

    def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """订阅主题."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Message], None]):
        """取消订阅."""
        if topic in self._subscribers:
            self._subscribers[topic].remove(callback)

    def subscribe_agent(self, agent_id: str, callback: Callable[[Message], None]):
        """订阅特定Agent的消息."""
        if agent_id not in self._agent_subscribers:
            self._agent_subscribers[agent_id] = []
        self._agent_subscribers[agent_id].append(callback)

    def publish(self, message: Message):
        """发布消息."""
        # 记录历史
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

        # 持久化到文件 (LCC JSONL 模式)
        if self._inbox_dir and message.receiver_id:
            self._persist_message(message)

        # 处理消息
        self._process_message(message)

    def _persist_message(self, message: Message):
        """将消息写入接收者的 JSONL 邮箱文件."""
        import json as _json
        path = f"{self._inbox_dir}/{message.receiver_id}.jsonl"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def read_inbox(self, agent_id: str) -> list[dict]:
        """读取并清空 agent 的邮箱 (LCC drain 模式)."""
        if not self._inbox_dir:
            return []
        import json as _json
        path = f"{self._inbox_dir}/{agent_id}.jsonl"
        try:
            from pathlib import Path
            p = Path(path)
            if not p.exists():
                return []
            msgs = [_json.loads(line) for line in p.read_text(encoding="utf-8").strip().splitlines() if line]
            p.write_text("")  # drain
            return msgs
        except Exception:
            return []

    def _process_message(self, message: Message):
        """处理消息."""
        # 1. 如果是广播，发送给所有订阅者
        if not message.receiver_id:
            self._broadcast(message)
            return

        # 2. 发送给特定Agent
        if message.receiver_id in self._agent_subscribers:
            for callback in self._agent_subscribers[message.receiver_id]:
                try:
                    callback(message)
                except Exception:
                    pass

        # 3. 发送给主题订阅者
        if message.topic in self._subscribers:
            for callback in self._subscribers[message.topic]:
                try:
                    callback(message)
                except Exception:
                    pass

    def _broadcast(self, message: Message):
        """广播消息."""
        # 发送给所有Agent订阅者
        for agent_id, callbacks in self._agent_subscribers.items():
            if agent_id != message.sender_id:  # 不发给自己
                for callback in callbacks:
                    try:
                        callback(message)
                    except Exception:
                        pass

        # 发送给主题订阅者
        if message.topic in self._subscribers:
            for callback in self._subscribers[message.topic]:
                try:
                    callback(message)
                except Exception:
                    pass

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        topic: str,
        payload: dict,
        msg_type: MessageType = MessageType.DATA,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Message:
        """发送消息."""
        message = Message(
            type=msg_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            topic=topic,
            payload=payload,
            priority=priority,
        )
        self.publish(message)
        return message

    def request_response(
        self,
        sender_id: str,
        receiver_id: str,
        topic: str,
        payload: dict,
        timeout: float = 5.0,
    ) -> Optional[Message]:
        """请求-响应模式."""
        import threading

        response = None
        event = threading.Event()

        def on_response(msg: Message):
            nonlocal response
            if msg.reply_to and msg.receiver_id == sender_id:
                response = msg
                event.set()

        # 订阅响应
        self.subscribe_agent(sender_id, on_response)

        # 发送请求
        request_msg = self.send_message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            topic=topic,
            payload=payload,
            msg_type=MessageType.REQUEST,
        )

        # 等待响应
        event.wait(timeout)

        # 取消订阅
        self.unsubscribe_agent(sender_id, on_response)

        return response

    def unsubscribe_agent(self, agent_id: str, callback: Callable[[Message], None]):
        """取消Agent订阅."""
        if agent_id in self._agent_subscribers:
            self._agent_subscribers[agent_id].remove(callback)

    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 100,
    ) -> list[Message]:
        """获取消息历史."""
        messages = self._message_history

        if agent_id:
            messages = [
                m for m in messages
                if m.sender_id == agent_id or m.receiver_id == agent_id
            ]

        if topic:
            messages = [m for m in messages if m.topic == topic]

        return messages[-limit:]

    def get_stats(self) -> dict:
        """获取统计信息."""
        return {
            "total_messages": len(self._message_history),
            "subscribed_topics": list(self._subscribers.keys()),
            "subscribed_agents": list(self._agent_subscribers.keys()),
        }


class AgentCommunicator:
    """Agent通信器 - 为Agent提供通信接口."""

    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self._pending_responses: dict[str, Message] = {}

        # 订阅自己的消息
        self.message_bus.subscribe_agent(agent_id, self._on_message)

    def _on_message(self, message: Message):
        """处理收到的消息."""
        if message.reply_to:
            self._pending_responses[message.reply_to] = message

    def send(self, receiver_id: str, topic: str, payload: dict, **kwargs) -> Message:
        """发送消息."""
        return self.message_bus.send_message(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            topic=topic,
            payload=payload,
            **kwargs,
        )

    def broadcast(self, topic: str, payload: dict, **kwargs) -> Message:
        """广播消息."""
        return self.message_bus.send_message(
            sender_id=self.agent_id,
            receiver_id="",  # 空表示广播
            topic=topic,
            payload=payload,
            **kwargs,
        )

    def request(self, receiver_id: str, topic: str, payload: dict, timeout: float = 5.0) -> Optional[Message]:
        """请求消息."""
        return self.message_bus.request_response(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            topic=topic,
            payload=payload,
            timeout=timeout,
        )

    def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """订阅主题."""
        self.message_bus.subscribe(topic, callback)

    def on(self, topic: str, callback: Callable[[Message], None]):
        """订阅主题 (on别名)."""
        self.subscribe(topic, callback)
