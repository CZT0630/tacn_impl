"""资源监控."""

from __future__ import annotations

from typing import Optional

from backend.core.models import Location
from backend.infrastructure.node import NodeStatus


class ResourceMonitor:
    """资源监控 - 资源控制面的底层支撑.

    维护所有节点的资源状态快照.
    """

    def __init__(self):
        self._nodes: dict[str, NodeStatus] = {}

    def register_node(self, node: NodeStatus):
        """注册节点."""
        self._nodes[node.node_id] = node

    def unregister_node(self, node_id: str) -> bool:
        """注销节点."""
        return self._nodes.pop(node_id, None) is not None

    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        """获取节点状态."""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[NodeStatus]:
        """获取所有节点."""
        return list(self._nodes.values())

    def get_online_nodes(self) -> list[NodeStatus]:
        """获取在线节点."""
        return [n for n in self._nodes.values() if n.is_online]

    def get_nodes_by_location(self, location: Location) -> list[NodeStatus]:
        """按位置获取节点."""
        return [n for n in self._nodes.values() if n.location == location]

    def update_node(self, node_id: str, **kwargs) -> bool:
        """更新节点状态."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        for k, v in kwargs.items():
            if hasattr(node, k):
                setattr(node, k, v)
        return True

    def get_average_load(self, location: Location) -> float:
        """获取指定位置的平均 CPU 负载."""
        nodes = self.get_nodes_by_location(location)
        if not nodes:
            return 0.0
        return sum(n.cpu_usage for n in nodes) / len(nodes)

    def get_total_queue_depth(self, location: Location) -> int:
        """获取指定位置的总队列深度."""
        return sum(n.queue_depth for n in self.get_nodes_by_location(location))
