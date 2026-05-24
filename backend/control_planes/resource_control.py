"""资源控制面."""

from __future__ import annotations

from backend.core.models import Location
from backend.infrastructure.network import NetworkModel
from backend.infrastructure.resource_monitor import ResourceMonitor
from backend.registry.agent_registry import AgentRegistry


class ResourceControlPlane:
    """资源控制面.

    职责: 终端资源监测、边缘负载感知、云端资源调度、
    链路状态监测、队列估计、能耗管理、网络切片、拥塞控制.

    回答: 当前哪些资源可用？哪些资源拥塞？
    """

    def __init__(
        self,
        network_model: NetworkModel,
        resource_monitor: ResourceMonitor,
        agent_registry: AgentRegistry,
    ):
        self.network_model = network_model
        self.resource_monitor = resource_monitor
        self.agent_registry = agent_registry

    def get_resource_status(self) -> dict:
        """获取全局资源状态快照."""
        nodes = self.resource_monitor.get_all_nodes()
        return {
            "total_nodes": len(nodes),
            "online_nodes": sum(1 for n in nodes if n.is_online),
            "by_location": {
                loc.value: {
                    "count": len(
                        self.resource_monitor.get_nodes_by_location(loc)
                    ),
                    "avg_cpu": self.resource_monitor.get_average_load(loc),
                }
                for loc in Location
            },
            "agent_stats": self.agent_registry.get_statistics(),
        }

    def get_congestion_report(self) -> dict:
        """获取拥塞报告."""
        report = {}
        for loc in Location:
            avg_load = self.resource_monitor.get_average_load(loc)
            report[loc.value] = {
                "avg_load": avg_load,
                "congested": avg_load > 0.8,
            }
        return report

    def estimate_end_to_end_latency(
        self, src: Location, dst: Location, computation_ms: float
    ) -> float:
        """估算端到端时延."""
        network = self.network_model.get_latency(src, dst)
        return network + computation_ms

    def get_network_links(self) -> dict:
        """获取所有网络链路属性."""
        links = self.network_model.get_all_links()
        return {
            f"{src.value}->{dst.value}": {
                "latency_ms": prop.latency_ms,
                "bandwidth_mbps": prop.bandwidth_mbps,
            }
            for (src, dst), prop in links.items()
        }
