"""DataPool — 时序数据池，外部灌入、工具读取.

外部通过 HTTP POST 灌入传感器/摄像头/告警等数据，
Agent 工具从池中读取最新值或历史序列。

数据模型:
    source  = "sensor_001" / "camera_east_gate" / ...
    type    = "temperature" / "smoke" / "image" / "alert" / ...
    value   = 任意 JSON 可序列化对象
    ts      = 时间戳 (自动或手动)

用法:
    pool = DataPool.get_instance()
    pool.push("sensor_001", "temperature", 42.5)
    pool.push("camera_01", "image", {"url": "...", "objects": [...]})
    latest = pool.get_latest("sensor_001", "temperature")
    history = pool.get_history("sensor_001", "temperature", limit=10)
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataPoint:
    """单条数据点."""
    source: str
    type: str
    value: Any
    ts: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class DataPool:
    """时序数据池 — 线程安全，支持多源多类型.

    使用单例模式，全局唯一。
    """

    _instance: DataPool | None = None
    _lock = threading.Lock()

    def __init__(self, max_history_per_key: int = 200):
        self._max_history = max_history_per_key
        # key = (source, type) → deque of DataPoint
        self._data: dict[tuple[str, str], deque[DataPoint]] = defaultdict(
            lambda: deque(maxlen=max_history_per_key)
        )
        # 最新值快照
        self._latest: dict[tuple[str, str], DataPoint] = {}
        self._push_lock = threading.Lock()
        # 统计
        self._total_pushes = 0

    @classmethod
    def get_instance(cls) -> DataPool:
        """获取全局单例."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例 (测试用)."""
        with cls._lock:
            cls._instance = None

    # ========================================================================
    # 写入
    # ========================================================================

    def push(
        self,
        source: str,
        data_type: str,
        value: Any,
        ts: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DataPoint:
        """推入一条数据.

        Args:
            source: 数据源标识 (如 "sensor_001")
            data_type: 数据类型 (如 "temperature")
            value: 数据值 (任意 JSON 可序列化对象)
            ts: 时间戳，默认为当前时间
            metadata: 附加元数据

        Returns:
            创建的 DataPoint
        """
        dp = DataPoint(
            source=source,
            type=data_type,
            value=value,
            ts=ts or time.time(),
            metadata=metadata or {},
        )
        key = (source, data_type)
        with self._push_lock:
            self._data[key].append(dp)
            self._latest[key] = dp
            self._total_pushes += 1
        return dp

    def push_batch(self, items: list[dict[str, Any]]) -> int:
        """批量推入数据.

        每个 item 需包含 source, type, value 字段。
        可选 ts, metadata。

        Returns:
            成功推入的数量
        """
        count = 0
        for item in items:
            source = item.get("source")
            data_type = item.get("type")
            value = item.get("value")
            if source is None or data_type is None or value is None:
                continue
            self.push(
                source=source,
                data_type=data_type,
                value=value,
                ts=item.get("ts"),
                metadata=item.get("metadata"),
            )
            count += 1
        return count

    # ========================================================================
    # 读取
    # ========================================================================

    def get_latest(self, source: str, data_type: str) -> DataPoint | None:
        """获取指定源+类型的最新数据."""
        return self._latest.get((source, data_type))

    def get_latest_value(self, source: str, data_type: str, default=None) -> Any:
        """获取最新数据的值，不存在时返回 default."""
        dp = self.get_latest(source, data_type)
        return dp.value if dp else default

    def get_history(
        self,
        source: str,
        data_type: str,
        limit: int = 10,
        since: float | None = None,
    ) -> list[DataPoint]:
        """获取历史数据.

        Args:
            source: 数据源
            data_type: 数据类型
            limit: 最大返回条数
            since: 起始时间戳 (过滤)

        Returns:
            DataPoint 列表，按时间正序
        """
        key = (source, data_type)
        points = list(self._data.get(key, []))
        if since is not None:
            points = [p for p in points if p.ts >= since]
        # 返回最近 limit 条，按时间正序
        return sorted(points[-limit:], key=lambda p: p.ts)

    def get_all_latest(self) -> dict[str, Any]:
        """获取所有源的最新数据快照.

        Returns:
            {"source:type": value, ...}
        """
        return {
            f"{k[0]}:{k[1]}": v.value
            for k, v in self._latest.items()
        }

    def list_sources(self) -> list[str]:
        """列出所有数据源."""
        sources = set()
        for (source, _) in self._data.keys():
            sources.add(source)
        return sorted(sources)

    def list_types(self, source: str | None = None) -> list[str]:
        """列出数据类型 (可按 source 过滤)."""
        types = set()
        for (s, t) in self._data.keys():
            if source is None or s == source:
                types.add(t)
        return sorted(types)

    # ========================================================================
    # 管理
    # ========================================================================

    def clear(self, source: str | None = None, data_type: str | None = None):
        """清空数据.

        Args:
            source: 指定源清空，None 清空全部
            data_type: 指定类型清空，None 清空该源全部
        """
        with self._push_lock:
            if source is None:
                self._data.clear()
                self._latest.clear()
                return
            keys_to_remove = []
            for key in self._data:
                if key[0] == source:
                    if data_type is None or key[1] == data_type:
                        keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._data[key]
                self._latest.pop(key, None)

    def get_statistics(self) -> dict[str, Any]:
        """获取数据池统计."""
        return {
            "total_pushes": self._total_pushes,
            "active_keys": len(self._data),
            "sources": self.list_sources(),
            "total_points": sum(len(d) for d in self._data.values()),
        }
