"""网络时延/带宽/切片模型."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.core.models import Location


@dataclass
class LinkProperties:
    """链路属性."""

    latency_ms: float
    bandwidth_mbps: float
    jitter_ms: float = 0.0
    packet_loss_rate: float = 0.0


# 默认链路属性表
_DEFAULT_LINKS: dict[tuple[Location, Location], LinkProperties] = {
    (Location.TERMINAL, Location.TERMINAL): LinkProperties(latency_ms=2, bandwidth_mbps=100),
    (Location.TERMINAL, Location.PEER): LinkProperties(latency_ms=10, bandwidth_mbps=50),
    (Location.TERMINAL, Location.EDGE): LinkProperties(latency_ms=20, bandwidth_mbps=100),
    (Location.TERMINAL, Location.CLOUD): LinkProperties(latency_ms=80, bandwidth_mbps=50),
    (Location.PEER, Location.EDGE): LinkProperties(latency_ms=15, bandwidth_mbps=80),
    (Location.PEER, Location.CLOUD): LinkProperties(latency_ms=70, bandwidth_mbps=40),
    (Location.EDGE, Location.CLOUD): LinkProperties(latency_ms=40, bandwidth_mbps=200),
}


class NetworkModel:
    """网络模型.

    提供节点间时延、带宽、抖动等网络属性查询.
    """

    def __init__(self, custom_links: dict | None = None):
        self._links: dict[tuple[Location, Location], LinkProperties] = dict(_DEFAULT_LINKS)
        if custom_links:
            self._links.update(custom_links)

    def get_link(self, src: Location, dst: Location) -> LinkProperties:
        """获取两点间的链路属性."""
        key = (src, dst)
        if key in self._links:
            return self._links[key]
        # 对称
        reverse = (dst, src)
        if reverse in self._links:
            return self._links[reverse]
        # 默认
        return LinkProperties(latency_ms=50, bandwidth_mbps=50)

    def get_latency(self, src: Location, dst: Location) -> float:
        """获取单向时延 (ms)."""
        return self.get_link(src, dst).latency_ms

    def get_bandwidth(self, src: Location, dst: Location) -> float:
        """获取带宽 (Mbps)."""
        return self.get_link(src, dst).bandwidth_mbps

    def get_all_links(self) -> dict[tuple[Location, Location], LinkProperties]:
        """获取所有链路属性."""
        return dict(self._links)


class NetworkSlice:
    """网络切片.

    预留的网络资源片段，可为特定任务族或场景保证 QoS.
    """

    def __init__(
        self,
        slice_id: str,
        guaranteed_bandwidth_mbps: float,
        max_latency_ms: float,
    ):
        self.slice_id = slice_id
        self.guaranteed_bandwidth_mbps = guaranteed_bandwidth_mbps
        self.max_latency_ms = max_latency_ms
        self.assigned_tasks: list[str] = []

    def assign_task(self, task_id: str):
        """分配任务到切片."""
        if task_id not in self.assigned_tasks:
            self.assigned_tasks.append(task_id)

    def release_task(self, task_id: str):
        """释放任务."""
        if task_id in self.assigned_tasks:
            self.assigned_tasks.remove(task_id)

    @property
    def current_load(self) -> int:
        """当前切片上的任务数."""
        return len(self.assigned_tasks)
