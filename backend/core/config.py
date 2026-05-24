"""TACN 配置加载器."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TACNConfig:
    """TACN 配置加载器.

    加载 config.yaml (core catalog + 场景 catalog)
    和 experiment yaml (default.yaml / magazine.yaml).
    """

    def __init__(self, config_path: str | Path, *extra_paths: str | Path):
        self._raw: dict = {}
        for p in [config_path, *extra_paths]:
            self._raw = self._deep_merge(self._raw, self._load_yaml(Path(p)))
        self._core = self._raw.get("tacn_core", {})
        self._scenarios = self._raw.get("scenario_catalog", {})
        self._experiment = self._raw.get("experiment", {})

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        try:
            import yaml
        except ImportError:
            raise ImportError("需要安装 pyyaml 包: pip install pyyaml>=6.0")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _deep_merge(base: dict, overlay: dict) -> dict:
        """深度合并两个字典，overlay 覆盖 base."""
        result = dict(base)
        for k, v in overlay.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = TACNConfig._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    @property
    def core_catalog(self) -> dict[str, Any]:
        """TACN 核心 catalog: 意图模板、任务族、能力词表."""
        return self._core

    @property
    def scenario_catalog(self) -> dict[str, Any]:
        """场景实例 catalog: 智能校园/工厂/医院等."""
        return self._scenarios

    @property
    def experiment_config(self) -> dict[str, Any]:
        """实验配置: arrival_rate, num_tasks, ablation flags."""
        return self._experiment

    def get_intent_templates(self) -> dict[str, Any]:
        return self._core.get("intent_templates", {})

    def get_capability_vocabulary(self) -> dict[str, Any]:
        return self._core.get("capability_vocabulary", {})

    def get_task_families(self) -> dict[str, Any]:
        return self._core.get("task_families", {})

    def get_scenario(self, name: str) -> dict[str, Any] | None:
        return self._scenarios.get(name)

    def get_scenario_agents(self, name: str) -> list[dict[str, Any]]:
        scenario = self.get_scenario(name)
        if not scenario:
            return []
        return scenario.get("agents", [])

    def get_scenario_tools(self, name: str) -> list[str]:
        scenario = self.get_scenario(name)
        if not scenario:
            return []
        return scenario.get("tools", [])

    def get_ablation_flags(self) -> dict[str, bool]:
        return self._experiment.get("ablation_flags", {})

    def get_methods(self) -> list[str]:
        return self._experiment.get("methods", [])

    def get_num_tasks(self) -> int:
        return self._experiment.get("num_tasks", 50)

    def get_arrival_rate(self) -> float:
        return self._experiment.get("arrival_rate", 0.5)

    def get_seed(self) -> int:
        return self._experiment.get("seed", 42)

    def get_output_dir(self) -> str:
        return self._experiment.get("output_dir", "outputs/default")
