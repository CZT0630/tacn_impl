# TACN-Proto 代码对齐重构方案

> 目标：让代码向 README 描述的 TACN 核心能力靠拢（三控制面、双闭环、MTCC 联合编排）
> 创建日期：2026-05-24
> 状态：阶段一、二已完成，后续阶段待执行

---

## 一、现状分析摘要

### 1.1 已实现且符合 TACN 核心思想的部分

| TACN 环节 | 实现位置 | 完成度 |
|---|---|---|
| 意图解析 (Intent Parsing) | `backend/parser/intent_parser.py` | 三级回退：LLM tool-calling → LLM JSON → 关键词 mock |
| 子任务图生成 (Subtask Graph) | `backend/parser/subtask_builder.py` | 模板 DAG + 拓扑排序关键路径 |
| 智能体注册与能力画像 | `backend/registry/agent_registry.py` | 8 个默认 Agent，按 location/capability 索引 |
| 能力匹配路由 | `backend/router/capability_router.py` | 多准则打分（能力覆盖/时延/成本/隐私/负载） |
| 多智能体协作消息总线 | `backend/agent/message.py` | pub/sub + request-response + broadcast |
| 仿真执行与评估 | `backend/executor/simulation.py`, `backend/evaluation/metrics.py` | 随机时延抖动 + 成功率/P95/成本/隐私指标 |
| Baseline 对比方法 | `backend/baselines/` | CloudOnly、ResourceAwareCPN、SemanticRouter |

主链路 `intent → subtask graph → capability routing → collaborative execution` 可以跑通。

### 1.2 与 README 描述严重不符的部分

| 缺失项 | 影响 |
|---|---|
| 四层架构目录 (`backend/tacn/layers/`) | 代码是扁平包结构，不是 L1-L4 |
| 三个控制面 | 资源/语义/信任安全隐私控制面完全缺失 |
| 双闭环优化 | 无执行反馈回路，Agent 指标不更新 |
| MTCC 联合编排 | Router 只选 Agent，不选 model/tool/context |
| 终端智能体差异化 | 四种 Agent 行为完全相同，仅 metadata 标签不同 |
| 配置系统 (`configs/`) | 无 YAML 配置，全靠硬编码 |
| 实验脚本 (`scripts/`) | 无可复现实验流水线 |
| `tacn_core/` + `scenario_catalog/` | 场景无关核心 vs 场景适配器的概念未落地 |
| Streamlit 仪表盘 | 实际是纯 HTML + Chart.js |
| CLI 入口 | 实际是 FastAPI 服务器 |
| 测试 (`tests/`) | 无测试 |
| 输出系统 (`outputs/`) | 无结果导出 |
| 文档 (`docs/`) | README 引用的基准文档不存在 |

### 1.3 已知 Bug

| Bug | 位置 | 描述 |
|---|---|---|
| 类名错误 | `backend/orchestrator/engine.py:13-14` | 导入不存在的 `IntentParser`（应为 `LLMIntentParser`）和 `SubTaskGraphBuilder`（应为 `LLMSubTaskBuilder`），且同步调用 async 方法 |
| 缺少 await | `backend/api/experiments.py:77-83` | baseline 的 `process()` 是 async 但未 await |
| 方法不存在 | `examples/demo_agent.py:59`, `examples/demo_multi_agent.py:77` | 调用 `AgentManager` 上不存在的 `execute_plan()` 和 `get_agent_stats()` |

---

## 二、目标目录结构

采用扁平包结构，四层架构通过模块职责和 import 依赖表达，不使用目录前缀。

```text
tacn_impl/
├── pyproject.toml
├── requirements.txt                     # Python 依赖
├── .env.example                         # 环境变量模板
├── docs/
│   ├── tacn_project_outline.md          # 项目概念基准
│   ├── experiment_positioning.md        # 实验定位
│   └── tacn_alignment_plan.md           # 本文档
├── backend/
│   ├── main.py                          # FastAPI 应用入口
│   ├── core/
│   │   └── models.py                    # 核心数据模型（扩充：增加 MTCC 相关字段）
│   ├── parser/
│   │   ├── intent_parser.py             # 意图解析器
│   │   ├── subtask_builder.py           # 子任务图构建器
│   │   ├── validators.py
│   │   └── json_repair.py
│   ├── registry/
│   │   └── agent_registry.py            # 智能体注册表
│   ├── router/
│   │   └── capability_router.py         # 能力路由器
│   ├── orchestration/                   # 编排层（原 orchestrator/，已重命名）
│   │   ├── engine.py                    # 编排引擎
│   │   ├── tacn_system.py              # TACN 完整流水线
│   │   ├── mtcc_orchestrator.py         # MTCC 联合编排器（新增，核心创新）
│   │   └── feedback.py                  # 执行反馈与闭环更新（新增）
│   ├── agent/
│   │   ├── base.py
│   │   ├── llm_agent.py
│   │   ├── terminal_agent.py            # 增强：隐私过滤
│   │   ├── peer_agent.py                # 增强：D2D 协作
│   │   ├── edge_agent.py                # 增强：知识检索
│   │   ├── cloud_agent.py               # 增强：复杂推理
│   │   ├── factory.py
│   │   ├── message.py
│   │   └── tools.py
│   ├── control_planes/                  # 三个控制面（新增）
│   │   ├── resource_control.py
│   │   ├── semantic_control.py
│   │   └── trust_privacy_control.py
│   ├── baselines/
│   │   ├── cloud_only.py
│   │   ├── resource_aware_cpn.py
│   │   └── semantic_router.py
│   ├── simulation/                      # 仿真执行（原 executor/，已重命名）
│   │   └── simulation.py
│   ├── evaluation/
│   │   └── metrics.py
│   ├── workload/
│   │   └── generator.py
│   ├── llm/
│   │   ├── client.py
│   │   └── config.py
│   └── api/
│       ├── tasks.py
│       ├── agents.py
│       └── experiments.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
├── examples/
│   ├── demo.py
│   ├── demo_tacn.py
│   ├── demo_agent.py
│   ├── demo_multi_agent.py
│   └── demo_agent_communication.py
├── scripts/                             # 新增
│   ├── run_all_magazine_experiments.py
│   └── run_llm_agent_samples.py
├── tests/                               # 新增
└── outputs/                             # 新增
```

---

## 三、分阶段实施计划

### 阶段一：目录重命名 + Bug 修复（P0，已完成）

> 决策：不采用四层目录前缀（`backend/tacn/layers/l*_`），保持扁平包结构。
> 四层架构关系通过代码 import 依赖和文档表达。

#### 1.1 已完成的目录重命名

| 原路径 | 新路径 | 原因 |
|---|---|---|
| `backend/orchestrator/` | `backend/orchestration/` | `orchestration`（过程/模块）比 `orchestrator`（人）更准确 |
| `backend/executor/` | `backend/simulation/` | `simulation` 比 `executor` 更准确描述其职责 |

#### 1.2 已完成的 Bug 修复

| Bug | 修复 |
|---|---|
| `engine.py` 导入不存在的 `IntentParser`/`SubTaskGraphBuilder` | 改为 `LLMIntentParser`/`LLMSubTaskBuilder` |
| `engine.py` 同步调用 async `parse()`/`build()` | `process_request` 和 `process_intent` 改为 async |
| `experiments.py` 缺少 await | 所有 `process()` 调用加上 await |
| `demo_agent.py`/`demo_multi_agent.py` 调用不存在的方法 | 在 `AgentManager` 中补充 `execute_plan()` 和 `get_agent_stats()` |
| `demo.py` 非 async 函数调用 async 方法 | 所有 demo 函数改为 async |
| `demo_agent.py`/`demo_multi_agent.py` `execute_plan()` 未 await | 加上 await |
| `demo_agent_communication.py` 引用不存在的 `agent_manager.message_bus` | 改为 `agent_manager.factory.message_bus` |
| `demo_agent_communication.py` 调用不存在的 `get_agents_by_type` | 移除未使用的调用 |
| `simulation.py` `in_degree[st]` 用 SubTask 对象作 dict key | 改为 `in_degree[st.id]` |
| 8 个包缺少 `__init__.py` | 补充 `core/parser/registry/router/baselines/workload/evaluation/api` |

#### 1.3 已完成的 import 更新

所有引用 `backend.orchestrator` 和 `backend.executor` 的文件已更新为 `backend.orchestration` 和 `backend.simulation`。

仅发生了两处目录重命名，文件名保持不变（用户决策：当前文件名已足够合理）：

| 旧路径 | 新路径 |
|---|---|
| `backend/orchestrator/engine.py` | `backend/orchestration/engine.py` |
| `backend/orchestrator/tacn_system.py` | `backend/orchestration/tacn_system.py` |
| `backend/executor/simulation.py` | `backend/simulation/simulation.py` |

其余文件路径不变。

#### 1.4 修复已知 Bug

**Bug 1: `engine.py` 类名错误 + 同步调用 async**

`backend/orchestration/engine.py` 中导入不存在的 `IntentParser`/`SubTaskGraphBuilder`，改为 `LLMIntentParser`/`LLMSubTaskBuilder`；`process_request` 和 `process_intent` 改为 async。

**Bug 2: `experiments.py` 缺少 await**

```python
# backend/api/experiments.py
# 旧
result_cloud = cloud_only.process(request)
result_cpn = cpn_baseline.process(request)
result_semantic = semantic_router.process(request)

# 新
result_cloud = await cloud_only.process(request)
result_cpn = await cpn_baseline.process(request)
result_semantic = await semantic_router.process(request)
```

**Bug 3: `demo_agent.py` / `demo_multi_agent.py` 调用不存在的方法**

已在 `AgentManager`（`backend/agent/factory.py`）中补充 `execute_plan()` 和 `get_agent_stats()` 方法。

#### 1.5 验证标准

- [x] `backend/orchestrator/` → `backend/orchestration/` 重命名完成
- [x] `backend/executor/` → `backend/simulation/` 重命名完成
- [x] 所有 import 路径已更新
- [x] engine.py 类名和 async 问题已修复
- [x] experiments.py 缺少 await 已修复
- [x] demo 脚本已修复（async + 缺失方法）
- [x] README 项目结构已更新
- [x] 所有 demo 脚本能正常运行（5/5 PASS）

---

### 阶段二：配置系统 + L1 基础设施层（P1，2 天）

#### 2.1 配置加载器

新建 `backend/core/config.py`：

```python
"""TACN 配置加载器."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml


class TACNConfig:
    """TACN 配置加载器.

    加载 config.yaml (core catalog + 场景 catalog)
    和 experiment yaml (default.yaml / magazine.yaml)
    """

    def __init__(self, config_path: str):
        self._path = Path(config_path)
        self._raw = self._load_yaml(self._path)
        self._core = self._raw.get("tacn_core", {})
        self._scenarios = self._raw.get("scenario_catalog", {})
        self._experiment = self._raw.get("experiment", {})

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def core_catalog(self) -> dict:
        """TACN 核心 catalog: 意图模板、任务族、能力词表."""
        return self._core

    @property
    def scenario_catalog(self) -> dict:
        """场景实例 catalog: 智能校园/工厂/医院等."""
        return self._scenarios

    @property
    def experiment_config(self) -> dict:
        """实验配置: arrival_rate, num_tasks, ablation flags."""
        return self._experiment

    def get_intent_templates(self) -> dict:
        return self._core.get("intent_templates", {})

    def get_capability_vocabulary(self) -> dict:
        return self._core.get("capability_vocabulary", {})

    def get_task_families(self) -> dict:
        return self._core.get("task_families", {})

    def get_scenario(self, name: str) -> dict | None:
        return self._scenarios.get(name)

    def get_ablation_flags(self) -> dict:
        return self._experiment.get("ablation_flags", {})
```

#### 2.2 配置文件

**`configs/config.yaml`** — TACN 核心 catalog + 场景实例：

```yaml
tacn_core:
  intent_templates:
    event_response:
      description: "事件响应类意图"
      typical_keywords: ["报警", "异常", "紧急", "告警", "触发"]
      required_capabilities: [sensing, vision, reasoning, tool_calling]
      typical_subtask_count: [4, 8]
      default_privacy_level: confidential

    mobile_inspection:
      description: "移动巡检类意图"
      typical_keywords: ["巡检", "检查", "维护", "诊断", "设备"]
      required_capabilities: [sensing, vision, rag_retrieval]
      typical_subtask_count: [3, 6]
      default_privacy_level: internal

    collaborative_perception:
      description: "协同感知类意图"
      typical_keywords: ["摄像头", "监控", "跟踪", "识别", "融合"]
      required_capabilities: [vision, sensing, reasoning]
      typical_subtask_count: [4, 7]
      default_privacy_level: internal

    context_aware_decision:
      description: "上下文感知决策类意图"
      typical_keywords: ["分析", "预测", "建议", "决策", "检索"]
      required_capabilities: [rag_retrieval, reasoning, computation]
      typical_subtask_count: [3, 6]
      default_privacy_level: internal

    personal_assistant_service:
      description: "个人助手服务类意图"
      typical_keywords: ["安排", "通知", "提醒", "日程", "会议"]
      required_capabilities: [reasoning, tool_calling, notification]
      typical_subtask_count: [3, 5]
      default_privacy_level: confidential

  capability_vocabulary:
    sensing:
      description: "环境感知能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [2, 50]
    vision:
      description: "视觉理解能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [20, 200]
    audio:
      description: "音频处理能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [10, 100]
    reasoning:
      description: "推理判断能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [100, 1000]
    planning:
      description: "规划能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [50, 500]
    tool_calling:
      description: "工具调用能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [20, 300]
    rag_retrieval:
      description: "RAG 检索能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [50, 500]
    notification:
      description: "通知能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [10, 100]
    control:
      description: "设备控制能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [50, 500]
    computation:
      description: "计算能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [10, 200]
    communication:
      description: "通信能力"
      quality_range: [0.0, 1.0]
      typical_latency_ms: [5, 50]

  task_families:
    event_response:
      required_capabilities: [sensing, vision, reasoning, tool_calling]
      typical_subtasks: 5-8
      privacy_level: confidential
    mobile_inspection:
      required_capabilities: [sensing, vision, rag_retrieval]
      typical_subtasks: 3-6
      privacy_level: internal
    collaborative_perception:
      required_capabilities: [vision, sensing, reasoning]
      typical_subtasks: 4-7
      privacy_level: internal
    context_aware_decision:
      required_capabilities: [rag_retrieval, reasoning, computation]
      typical_subtasks: 3-6
      privacy_level: internal
    personal_assistant_service:
      required_capabilities: [reasoning, tool_calling, notification]
      typical_subtasks: 3-5
      privacy_level: confidential

scenario_catalog:
  smart_campus:
    description: "智慧园区应急响应"
    agents:
      - {name: "campus_sensor_001", location: terminal, capabilities: [sensing]}
      - {name: "campus_camera_001", location: terminal, capabilities: [vision]}
      - {name: "campus_edge_security", location: edge, capabilities: [vision, reasoning]}
      - {name: "campus_edge_rag", location: edge, capabilities: [rag_retrieval]}
      - {name: "campus_cloud_llm", location: cloud, capabilities: [reasoning, tool_calling]}
    tools: [fire_alarm_api, notification_service, security_rules_db]

  smart_factory:
    description: "智慧工厂智能运维"
    agents:
      - {name: "factory_sensor_001", location: terminal, capabilities: [sensing]}
      - {name: "factory_camera_001", location: terminal, capabilities: [vision]}
      - {name: "factory_robot_001", location: peer, capabilities: [vision, sensing, control]}
      - {name: "factory_edge_vision", location: edge, capabilities: [vision, reasoning]}
      - {name: "factory_edge_rag", location: edge, capabilities: [rag_retrieval]}
      - {name: "factory_cloud_llm", location: cloud, capabilities: [reasoning, planning]}
    tools: [plc_gateway, work_order_system, notification_service, quality_tracker]

  personal_assistant:
    description: "个人智能助手服务"
    agents:
      - {name: "phone_agent_001", location: terminal, capabilities: [sensing, audio, tool_calling]}
      - {name: "edge_rag_agent", location: edge, capabilities: [rag_retrieval]}
      - {name: "cloud_llm_agent", location: cloud, capabilities: [reasoning, planning]}
    tools: [calendar_api, map_service, notification_service, contact_db]
```

**`configs/default.yaml`** — 默认实验：

```yaml
experiment:
  name: "default"
  description: "默认小规模实验"
  seed: 42
  num_tasks: 50
  arrival_rate: 0.5
  methods:
    - cloud_only
    - resource_aware_cpn
    - semantic_router
    - tacn_o
  ablation_flags:
    llm_intent: true
    capability_matching: true
    resource_awareness: true
    tool_context_awareness: true
    terminal_agents: true
  output_dir: "outputs/default"
```

**`configs/magazine.yaml`** — 全量实验：

```yaml
experiment:
  name: "magazine"
  description: "Magazine 论文全量实验"
  seed: 42
  num_tasks: 200
  arrival_rate: 1.0
  methods:
    - cloud_only
    - resource_aware_cpn
    - semantic_router
    - tacn_o
  ablation_flags:
    llm_intent: true
    capability_matching: true
    resource_awareness: true
    tool_context_awareness: true
    terminal_agents: true
  sensitivity:
    arrival_rates: [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
  output_dir: "outputs/magazine"
```

#### 2.3 L1 网络模型

新建 `backend/infrastructure/network.py`：

```python
"""网络时延/带宽/切片模型."""
from __future__ import annotations
from dataclasses import dataclass, field
from backend.tacn.core.models import Location


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
    (Location.TERMINAL, Location.PEER):     LinkProperties(latency_ms=10, bandwidth_mbps=50),
    (Location.TERMINAL, Location.EDGE):     LinkProperties(latency_ms=20, bandwidth_mbps=100),
    (Location.TERMINAL, Location.CLOUD):    LinkProperties(latency_ms=80, bandwidth_mbps=50),
    (Location.PEER, Location.EDGE):         LinkProperties(latency_ms=15, bandwidth_mbps=80),
    (Location.PEER, Location.CLOUD):        LinkProperties(latency_ms=70, bandwidth_mbps=40),
    (Location.EDGE, Location.CLOUD):        LinkProperties(latency_ms=40, bandwidth_mbps=200),
}


class NetworkModel:
    """网络模型.

    提供节点间时延、带宽、抖动等网络属性查询.
    """

    def __init__(self, custom_links: dict | None = None):
        self._links = dict(_DEFAULT_LINKS)
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


class NetworkSlice:
    """网络切片.

    预留的网络资源片段，可为特定任务族或场景保证 QoS.
    """

    def __init__(self, slice_id: str, guaranteed_bandwidth_mbps: float,
                 max_latency_ms: float):
        self.slice_id = slice_id
        self.guaranteed_bandwidth_mbps = guaranteed_bandwidth_mbps
        self.max_latency_ms = max_latency_ms
        self.assigned_tasks: list[str] = []
```

新建 `backend/infrastructure/node.py`：

```python
"""节点资源状态模型."""
from __future__ import annotations
from pydantic import BaseModel, Field
from backend.tacn.core.models import Location


class NodeStatus(BaseModel):
    """节点资源状态."""
    node_id: str
    location: Location
    cpu_usage: float = Field(0.0, ge=0.0, le=1.0)
    memory_usage: float = Field(0.0, ge=0.0, le=1.0)
    gpu_usage: float = Field(0.0, ge=0.0, le=1.0)
    queue_depth: int = 0
    energy_remaining: float = Field(1.0, ge=0.0, le=1.0)
    is_online: bool = True
```

新建 `backend/infrastructure/resource_monitor.py`：

```python
"""资源监控."""
from __future__ import annotations
from typing import Optional
from .node import NodeStatus
from backend.tacn.core.models import Location


class ResourceMonitor:
    """资源监控 - 资源控制面的底层支撑.

    维护所有节点的资源状态快照.
    """

    def __init__(self):
        self._nodes: dict[str, NodeStatus] = {}

    def register_node(self, node: NodeStatus):
        self._nodes[node.node_id] = node

    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[NodeStatus]:
        return list(self._nodes.values())

    def get_nodes_by_location(self, location: Location) -> list[NodeStatus]:
        return [n for n in self._nodes.values() if n.location == location]

    def update_node(self, node_id: str, **kwargs) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        for k, v in kwargs.items():
            if hasattr(node, k):
                setattr(node, k, v)
        return True

    def get_average_load(self, location: Location) -> float:
        nodes = self.get_nodes_by_location(location)
        if not nodes:
            return 0.0
        return sum(n.cpu_usage for n in nodes) / len(nodes)
```

#### 2.4 CLI 入口

新建根目录 `main.py`：

```python
"""TACN-Proto CLI 入口."""
from __future__ import annotations
import argparse
import asyncio


def run_experiment(config_path: str):
    """运行实验."""
    from backend.tacn.core.config import TACNConfig
    config = TACNConfig(config_path)
    print(f"Running experiment: {config.experiment_config.get('name', 'unnamed')}")
    # TODO: 实现阶段五后接入完整实验流水线
    raise NotImplementedError("实验流水线待阶段五实现")


def generate_plots(results_path: str, outdir: str):
    """生成图表."""
    print(f"Generating plots from {results_path} to {outdir}")
    # TODO: 实现阶段六后接入图表生成
    raise NotImplementedError("图表生成待阶段六实现")


def start_server(port: int):
    """启动 FastAPI 服务."""
    import uvicorn
    uvicorn.run("backend.tacn.api.app:app", host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser(description="TACN-Proto")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="运行实验")
    run_p.add_argument("--config", required=True, help="配置文件路径")

    plot_p = subparsers.add_parser("plot", help="生成图表")
    plot_p.add_argument("--results", required=True, help="结果 CSV 路径")
    plot_p.add_argument("--outdir", default="outputs/figures", help="输出目录")

    serve_p = subparsers.add_parser("serve", help="启动 FastAPI 服务")
    serve_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "run":
        run_experiment(args.config)
    elif args.command == "plot":
        generate_plots(args.results, args.outdir)
    elif args.command == "serve":
        start_server(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

#### 2.5 补充文件

`requirements.txt`：

```text
pydantic>=2.0
networkx>=3.0
fastapi>=0.100
uvicorn>=0.23
matplotlib>=3.5
openai>=1.0
jinja2>=3.1
pyyaml>=6.0
```

`.env.example`：

```env
TACN_API_KEY=your-api-key-here
TACN_BASE_URL=https://api.openai.com/v1
TACN_MODEL=gpt-4o-mini
TACN_USE_REAL_LLM=false
```

#### 2.6 验证标准

- [x] `python main.py run --config configs/default.yaml` 能解析配置（即使实验逻辑未完成）
- [x] `python main.py serve` 能启动 FastAPI
- [x] 配置文件能正确加载并返回 core_catalog / scenario_catalog / experiment_config
- [x] NetworkModel 能正确返回各位置间的时延和带宽

---

### 阶段三：L2 智能体抽象层 + Registry 体系（P1，2-3 天）

#### 3.1 扩充 AgentProfile

在 `backend/core/models.py` 中为 `AgentProfile` 增加字段：

```python
class AgentProfile(BaseModel):
    # ---- 现有字段保留 ----
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: Location
    description: str = ""
    capabilities: list[AgentCapability] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    context_access: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = Field(1, ge=1)
    current_load: float = Field(0.0, ge=0.0, le=1.0)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    avg_latency_ms: float = Field(100.0, ge=0.0)
    cost_per_invocation: float = Field(0.01, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ---- 新增: 模型能力 ----
    supported_models: list[str] = Field(default_factory=list)
    default_model: str = ""

    # ---- 新增: 上下文能力 ----
    context_sources: list[str] = Field(default_factory=list)
    context_capacity_kb: float = 0.0

    # ---- 新增: 可靠性指标 (由反馈回路更新) ----
    reliability_score: float = Field(1.0, ge=0.0, le=1.0)
    observed_latency_ms: float = 0.0
    tool_success_rate: float = Field(1.0, ge=0.0, le=1.0)
    context_hit_rate: float = Field(0.0, ge=0.0, le=1.0)
    routing_score: float = Field(0.5, ge=0.0, le=1.0)
```

#### 3.2 Model Registry

新建 `backend/registry/model_registry.py`：

```python
"""模型注册表."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    """模型画像."""
    id: str
    name: str
    model_type: str  # "lightweight", "vision", "rag", "llm"
    parameter_size: str = ""  # "1B", "7B", "70B"
    supported_tasks: list[str] = Field(default_factory=list)
    avg_latency_ms: float = 100.0
    cost_per_1k_tokens: float = 0.0
    quality_scores: dict[str, float] = Field(default_factory=dict)  # task_type -> quality
    max_context_length: int = 4096
    supports_tool_calling: bool = False
    metadata: dict = Field(default_factory=dict)


class ModelRegistry:
    """模型注册表.

    维护所有可用模型的画像，支持按任务类型/质量/成本查询.
    """

    def __init__(self):
        self._models: dict[str, ModelProfile] = {}

    def register(self, model: ModelProfile):
        self._models[model.id] = model

    def unregister(self, model_id: str) -> bool:
        return self._models.pop(model_id, None) is not None

    def get_model(self, model_id: str) -> Optional[ModelProfile]:
        return self._models.get(model_id)

    def get_all_models(self) -> list[ModelProfile]:
        return list(self._models.values())

    def find_models_for_task(self, task_type: str) -> list[ModelProfile]:
        """查找支持指定任务类型的模型."""
        return [m for m in self._models.values() if task_type in m.supported_tasks]

    def get_best_model(self, task_type: str, max_latency_ms: float = float("inf"),
                       max_cost: float = float("inf")) -> Optional[ModelProfile]:
        """获取最佳模型（按质量评分）."""
        candidates = [
            m for m in self.find_models_for_task(task_type)
            if m.avg_latency_ms <= max_latency_ms and m.cost_per_1k_tokens <= max_cost
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda m: m.quality_scores.get(task_type, 0.0))


def create_default_model_registry() -> ModelRegistry:
    """创建默认模型注册表."""
    registry = ModelRegistry()

    models = [
        ModelProfile(
            id="lightweight_sensing", name="轻量感知模型",
            model_type="lightweight", parameter_size="1B",
            supported_tasks=["sensing", "audio"],
            avg_latency_ms=20, cost_per_1k_tokens=0.001,
            quality_scores={"sensing": 0.7, "audio": 0.65},
        ),
        ModelProfile(
            id="vision_model", name="视觉理解模型",
            model_type="vision", parameter_size="3B",
            supported_tasks=["vision", "security_monitoring"],
            avg_latency_ms=80, cost_per_1k_tokens=0.005,
            quality_scores={"vision": 0.88, "security_monitoring": 0.82},
        ),
        ModelProfile(
            id="rag_model", name="RAG 检索模型",
            model_type="rag", parameter_size="7B",
            supported_tasks=["rag_retrieval", "context_aware_decision"],
            avg_latency_ms=150, cost_per_1k_tokens=0.003,
            quality_scores={"rag_retrieval": 0.85, "context_aware_decision": 0.8},
        ),
        ModelProfile(
            id="cloud_llm", name="云端大模型",
            model_type="llm", parameter_size="70B",
            supported_tasks=["reasoning", "planning", "tool_calling",
                             "emergency_response", "predictive_maintenance"],
            avg_latency_ms=400, cost_per_1k_tokens=0.02,
            quality_scores={"reasoning": 0.95, "planning": 0.92, "tool_calling": 0.88},
            supports_tool_calling=True,
        ),
    ]

    for m in models:
        registry.register(m)
    return registry
```

#### 3.3 Tool Registry

新建 `backend/registry/tool_registry.py`：

```python
"""工具注册表."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from backend.tacn.core.models import PrivacyLevel, CapabilityType


class ToolProfile(BaseModel):
    """工具画像."""
    id: str
    name: str
    tool_type: str  # "api", "device_control", "data_source", "notification"
    description: str = ""
    input_schema: dict = Field(default_factory=dict)
    avg_latency_ms: float = 50.0
    success_rate: float = 0.95
    privacy_impact: PrivacyLevel = PrivacyLevel.INTERNAL
    required_permissions: list[str] = Field(default_factory=list)
    related_capabilities: list[CapabilityType] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ToolRegistry:
    """工具注册表.

    维护所有可用工具的画像，支持按能力/隐私影响查询.
    """

    def __init__(self):
        self._tools: dict[str, ToolProfile] = {}

    def register(self, tool: ToolProfile):
        self._tools[tool.id] = tool

    def unregister(self, tool_id: str) -> bool:
        return self._tools.pop(tool_id, None) is not None

    def get_tool(self, tool_id: str) -> Optional[ToolProfile]:
        return self._tools.get(tool_id)

    def get_all_tools(self) -> list[ToolProfile]:
        return list(self._tools.values())

    def find_tools_for_capability(self, cap_type: CapabilityType) -> list[ToolProfile]:
        """查找与指定能力相关的工具."""
        return [t for t in self._tools.values() if cap_type in t.related_capabilities]

    def find_tools_by_type(self, tool_type: str) -> list[ToolProfile]:
        """按类型查找工具."""
        return [t for t in self._tools.values() if t.tool_type == tool_type]

    def check_privacy_compatible(self, tool_id: str,
                                  max_privacy: PrivacyLevel) -> bool:
        """检查工具的隐私影响是否在允许范围内."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        privacy_order = {
            PrivacyLevel.PUBLIC: 0,
            PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2,
            PrivacyLevel.RESTRICTED: 3,
        }
        return privacy_order.get(tool.privacy_impact, 0) <= privacy_order.get(max_privacy, 3)


def create_default_tool_registry() -> ToolRegistry:
    """创建默认工具注册表."""
    registry = ToolRegistry()

    tools = [
        ToolProfile(id="camera", name="摄像头", tool_type="device_control",
                     avg_latency_ms=30, related_capabilities=[CapabilityType.VISION]),
        ToolProfile(id="temperature_sensor", name="温度传感器", tool_type="device_control",
                     avg_latency_ms=5, related_capabilities=[CapabilityType.SENSING]),
        ToolProfile(id="smoke_detector", name="烟雾探测器", tool_type="device_control",
                     avg_latency_ms=3, related_capabilities=[CapabilityType.SENSING]),
        ToolProfile(id="vector_database", name="向量数据库", tool_type="data_source",
                     avg_latency_ms=80, related_capabilities=[CapabilityType.RAG_RETRIEVAL]),
        ToolProfile(id="document_store", name="文档存储", tool_type="data_source",
                     avg_latency_ms=100, related_capabilities=[CapabilityType.RAG_RETRIEVAL]),
        ToolProfile(id="notification_service", name="通知服务", tool_type="api",
                     avg_latency_ms=50, related_capabilities=[CapabilityType.NOTIFICATION]),
        ToolProfile(id="work_order_system", name="工单系统", tool_type="api",
                     avg_latency_ms=80, related_capabilities=[CapabilityType.TOOL_CALLING]),
        ToolProfile(id="llm_api", name="LLM API", tool_type="api",
                     avg_latency_ms=300, related_capabilities=[CapabilityType.REASONING]),
    ]

    for t in tools:
        registry.register(t)
    return registry
```

#### 3.4 Context Registry

新建 `backend/registry/context_registry.py`：

```python
"""上下文注册表."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from backend.tacn.core.models import Location, PrivacyLevel


class ContextSource(BaseModel):
    """上下文源."""
    id: str
    name: str
    context_type: str  # "user_profile", "environment", "device_state", "history", "knowledge_base"
    location: Location  # 数据所在位置
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    access_cost_ms: float = 10.0
    size_kb: float = 0.0
    description: str = ""
    metadata: dict = Field(default_factory=dict)


class ContextRegistry:
    """上下文注册表.

    维护所有可用上下文源，支持按类型/位置/隐私级别查询.
    """

    def __init__(self):
        self._sources: dict[str, ContextSource] = {}

    def register(self, source: ContextSource):
        self._sources[source.id] = source

    def unregister(self, source_id: str) -> bool:
        return self._sources.pop(source_id, None) is not None

    def get_context(self, context_id: str) -> Optional[ContextSource]:
        return self._sources.get(context_id)

    def get_all_sources(self) -> list[ContextSource]:
        return list(self._sources.values())

    def find_by_type(self, context_type: str) -> list[ContextSource]:
        return [s for s in self._sources.values() if s.context_type == context_type]

    def find_by_location(self, location: Location) -> list[ContextSource]:
        return [s for s in self._sources.values() if s.location == location]

    def find_for_task(self, required_context: list[str],
                       max_privacy: PrivacyLevel = PrivacyLevel.RESTRICTED
                       ) -> list[ContextSource]:
        """查找任务所需的上下文源."""
        privacy_order = {
            PrivacyLevel.PUBLIC: 0, PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2, PrivacyLevel.RESTRICTED: 3,
        }
        max_level = privacy_order.get(max_privacy, 3)
        return [
            s for s in self._sources.values()
            if s.id in required_context
            and privacy_order.get(s.privacy_level, 0) <= max_level
        ]


def create_default_context_registry() -> ContextRegistry:
    """创建默认上下文注册表."""
    registry = ContextRegistry()

    sources = [
        ContextSource(id="user_profile", name="用户画像", context_type="user_profile",
                       location=Location.TERMINAL, privacy_level=PrivacyLevel.CONFIDENTIAL),
        ContextSource(id="location_history", name="位置历史", context_type="history",
                       location=Location.TERMINAL, privacy_level=PrivacyLevel.CONFIDENTIAL),
        ContextSource(id="sensor_history", name="传感器历史", context_type="history",
                       location=Location.EDGE, privacy_level=PrivacyLevel.INTERNAL),
        ContextSource(id="maintenance_records", name="维护记录", context_type="knowledge_base",
                       location=Location.EDGE, privacy_level=PrivacyLevel.INTERNAL),
        ContextSource(id="local_knowledge_base", name="本地知识库", context_type="knowledge_base",
                       location=Location.EDGE, privacy_level=PrivacyLevel.INTERNAL),
        ContextSource(id="global_knowledge_base", name="全局知识库", context_type="knowledge_base",
                       location=Location.CLOUD, privacy_level=PrivacyLevel.INTERNAL),
        ContextSource(id="security_policies", name="安全策略", context_type="knowledge_base",
                       location=Location.CLOUD, privacy_level=PrivacyLevel.INTERNAL),
        ContextSource(id="network_state", name="网络状态", context_type="environment",
                       location=Location.EDGE, privacy_level=PrivacyLevel.PUBLIC),
    ]

    for s in sources:
        registry.register(s)
    return registry
```

#### 3.5 增强 Agent 默认注册

更新 `backend/registry/registry.py` 中的 `create_default_registry()`，为每个 Agent 增加 `supported_models`、`context_sources` 字段。同时增加 `reliability_score` 等反馈字段的初始值。

#### 3.6 AgentRuntime 抽象层

**设计目标：** 将 Agent 实现与编排层解耦。编排层通过 `AgentRuntime` 接口调度 Agent，不关心具体实现（当前 mock、未来 Claude SDK / LangGraph / 自研均可）。后续选定 Agent 框架后，只需新增一个 runtime 实现，编排层零改动。

新建 `backend/agent/runtime.py`：

```python
"""Agent 运行时抽象 - 编排层的调度目标."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from backend.core.models import (
    AgentCapability,
    CapabilityType,
    ExecutionPlan,
    SubTask,
    SubTaskResult,
)


class AgentRuntime(ABC):
    """Agent 运行时接口.

    编排层（OrchestrationEngine / MTCCOrchestrator）通过此接口调度 Agent，
    不依赖具体的 Agent 实现（LLMAgent / Claude SDK / LangGraph 等）。
    """

    @abstractmethod
    async def execute(self, subtask: SubTask, context: dict[str, Any] | None = None) -> SubTaskResult:
        """执行单个子任务.

        Args:
            subtask: 子任务定义
            context: 执行上下文（上游结果、环境信息等）

        Returns:
            子任务执行结果
        """
        ...

    @abstractmethod
    async def execute_plan(self, plan: ExecutionPlan) -> dict[str, Any]:
        """执行整个计划（含并行组调度）.

        Args:
            plan: 完整执行计划

        Returns:
            执行摘要 {"status", "total_latency_ms", "total_cost", "results"}
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list[CapabilityType]:
        """声明当前 runtime 支持的能力列表."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """获取运行时统计信息（可选覆写）."""
        return {}
```

将现有实现包装为 `MockAgentRuntime`：

```python
"""MockAgentRuntime - 基于现有 LLMAgent 的运行时实现."""
from backend.agent.runtime import AgentRuntime
from backend.agent.factory import AgentManager
from backend.registry.agent_registry import AgentRegistry


class MockAgentRuntime(AgentRuntime):
    """基于当前 LLMAgent mock 的运行时实现.

    包装现有 AgentManager，对外暴露 AgentRuntime 接口。
    """

    def __init__(self, registry: AgentRegistry):
        self._manager = AgentManager(registry)
        self._manager.initialize()

    async def execute(self, subtask, context=None):
        # 委派给对应 Agent 执行
        ...

    async def execute_plan(self, plan):
        return await self._manager.execute_plan(plan)

    def get_capabilities(self):
        return self._manager.get_available_capabilities()

    def get_stats(self):
        return self._manager.get_agent_stats()
```

编排层改造（阶段四）：`OrchestrationEngine` / `MTCCOrchestrator` 构造时接收 `AgentRuntime` 而非 `AgentManager`。

```
OrchestrationEngine(registry, runtime: AgentRuntime)
                          │
                          ▼
                   runtime.execute_plan(plan)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   MockAgentRuntime  ClaudeAgentRuntime  LangGraphRuntime
   (当前 mock)       (未来接入)         (未来接入)
```

#### 3.7 验证标准

- [ ] `ModelRegistry` 能注册/查询/按任务类型筛选模型
- [ ] `ToolRegistry` 能注册/查询/按能力筛选工具
- [ ] `ContextRegistry` 能注册/查询/按位置和隐私级别筛选上下文源
- [ ] `AgentProfile` 包含完整的模型/工具/上下文/反馈字段
- [ ] `create_default_registry()` 返回增强后的 Agent 列表
- [ ] `AgentRuntime` 接口定义完成（execute / execute_plan / get_capabilities）
- [ ] `MockAgentRuntime` 包装现有 AgentManager，所有 demo 脚本通过
- [ ] 编排层可选依赖 `AgentRuntime` 接口（阶段四改造，此阶段仅定义接口）

---

### 阶段四：L3 编排层 — MTCC 联合编排 + 控制面（P0，3-4 天）

#### 4.1 MTCC 联合编排器

新建 `backend/orchestration/mtcc_orchestrator.py`：

这是 TACN 的**核心创新模块**。当前 `capability_router.py` 只选 Agent，MTCC 为每个子任务**同时**决定 agent + model + tool + context + compute_tier + privacy_action + execution_mode。

```python
"""MTCC 联合编排器 - 模型-工具-算力-上下文联合编排."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field

from backend.tacn.core.models import (
    AgentProfile, CapabilityType, Location, PrivacyLevel, SubTask, SubTaskGraph,
)
from backend.tacn.layers.l2_terminal_agents.registry import AgentRegistry
from backend.tacn.layers.l2_terminal_agents.model_registry import ModelRegistry
from backend.tacn.layers.l2_terminal_agents.tool_registry import ToolRegistry
from backend.tacn.layers.l2_terminal_agents.context_registry import ContextRegistry
from backend.tacn.layers.l1_infrastructure.network import NetworkModel


class MTCCDecision(BaseModel):
    """MTCC 联合决策结果."""
    subtask_id: str
    selected_agent_id: str
    selected_model: str
    selected_tools: list[str] = Field(default_factory=list)
    selected_context: list[str] = Field(default_factory=list)
    selected_compute_tier: Location = Location.EDGE
    privacy_action: str = "allow_remote"  # "local_only" | "anonymize" | "allow_remote"
    execution_mode: str = "direct"  # "direct" | "delegated" | "collaborative"
    estimated_latency_ms: float = 0.0
    estimated_cost: float = 0.0
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)


@dataclass
class MTCCConfig:
    """MTCC 编排配置."""
    capability_weight: float = 0.25
    model_quality_weight: float = 0.20
    tool_coverage_weight: float = 0.10
    context_relevance_weight: float = 0.10
    latency_weight: float = 0.15
    cost_weight: float = 0.10
    privacy_weight: float = 0.10
    location_preferences: dict[Location, float] = field(default_factory=lambda: {
        Location.TERMINAL: 0.9, Location.PEER: 0.8,
        Location.EDGE: 0.7, Location.CLOUD: 0.5,
    })


class MTCCOrchestrator:
    """模型-工具-算力-上下文联合编排器.

    为每个子任务同时决定:
    - selected_agent: 由哪个智能体执行
    - selected_model: 使用哪个模型
    - selected_tools: 调用哪些工具
    - selected_context: 使用哪些上下文源
    - selected_compute_tier: 在哪个计算层执行
    - privacy_action: 隐私处理方式
    - execution_mode: 执行模式
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        context_registry: ContextRegistry,
        network_model: NetworkModel,
        config: Optional[MTCCConfig] = None,
    ):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.context_registry = context_registry
        self.network_model = network_model
        self.config = config or MTCCConfig()

    def orchestrate_subtask(self, subtask: SubTask) -> Optional[MTCCDecision]:
        """为单个子任务做出 MTCC 联合决策."""
        candidates = self._get_candidate_agents(subtask)
        if not candidates:
            return None

        best_decision = None
        best_score = -1.0

        for agent in candidates:
            decision = self._evaluate_candidate(subtask, agent)
            if decision and decision.score > best_score:
                best_score = decision.score
                best_decision = decision

        return best_decision

    def orchestrate_graph(self, graph: SubTaskGraph) -> list[MTCCDecision]:
        """为整个子任务图做出 MTCC 联合决策."""
        decisions = []
        agent_load: dict[str, float] = {}

        # 拓扑排序
        in_degree = {st.id: 0 for st in graph.subtasks}
        for edge in graph.edges:
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        queue = [st.id for st in graph.subtasks if in_degree[st.id] == 0]
        topo_order = []

        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            for edge in graph.edges:
                if edge.source_id == node:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append(edge.target_id)

        for subtask_id in topo_order:
            subtask = graph.get_subtask(subtask_id)
            if subtask is None:
                continue
            decision = self.orchestrate_subtask(subtask)
            if decision:
                decisions.append(decision)
                aid = decision.selected_agent_id
                agent_load[aid] = agent_load.get(aid, 0.0) + subtask.estimated_computation * 0.01

        return decisions

    # ---- 内部方法 ----

    def _get_candidate_agents(self, subtask: SubTask) -> list[AgentProfile]:
        """筛选候选 Agent."""
        candidates = []
        for agent in self.agent_registry.get_available_agents():
            # 能力匹配
            has_cap = any(
                agent.has_capability(req.capability_type)
                for req in subtask.required_capabilities
            )
            if not has_cap:
                continue
            # 隐私过滤
            privacy_order = {
                PrivacyLevel.PUBLIC: 0, PrivacyLevel.INTERNAL: 1,
                PrivacyLevel.CONFIDENTIAL: 2, PrivacyLevel.RESTRICTED: 3,
            }
            if privacy_order.get(agent.privacy_level, 0) < privacy_order.get(subtask.privacy_level, 0):
                continue
            candidates.append(agent)
        return candidates

    def _evaluate_candidate(self, subtask: SubTask, agent: AgentProfile) -> Optional[MTCCDecision]:
        """评估一个候选 Agent 的 MTCC 组合."""
        # 1. 模型选择
        selected_model = self._select_model(subtask, agent)

        # 2. 工具选择
        selected_tools = self._select_tools(subtask, agent)

        # 3. 上下文选择
        selected_context = self._select_context(subtask, agent)

        # 4. 计算位置
        compute_tier = agent.location

        # 5. 隐私决策
        privacy_action = self._decide_privacy(subtask, agent, compute_tier)

        # 6. 执行模式
        execution_mode = self._determine_execution_mode(subtask, agent)

        # 7. 综合评分
        scores = {}
        scores["capability"] = self._score_capability(subtask, agent)
        scores["model_quality"] = self._score_model_quality(subtask, selected_model)
        scores["tool_coverage"] = self._score_tool_coverage(subtask, selected_tools)
        scores["context_relevance"] = self._score_context_relevance(subtask, selected_context)
        scores["latency"] = self._score_latency(subtask, agent)
        scores["cost"] = self._score_cost(subtask, agent)
        scores["privacy"] = self._score_privacy(subtask, agent, privacy_action)

        cfg = self.config
        total_score = (
            scores["capability"] * cfg.capability_weight
            + scores["model_quality"] * cfg.model_quality_weight
            + scores["tool_coverage"] * cfg.tool_coverage_weight
            + scores["context_relevance"] * cfg.context_relevance_weight
            + scores["latency"] * cfg.latency_weight
            + scores["cost"] * cfg.cost_weight
            + scores["privacy"] * cfg.privacy_weight
        )
        total_score = min(1.0, total_score)

        estimated_latency = self._estimate_latency(subtask, agent)
        estimated_cost = self._estimate_cost(subtask, agent)

        return MTCCDecision(
            subtask_id=subtask.id,
            selected_agent_id=agent.id,
            selected_model=selected_model,
            selected_tools=selected_tools,
            selected_context=selected_context,
            selected_compute_tier=compute_tier,
            privacy_action=privacy_action,
            execution_mode=execution_mode,
            estimated_latency_ms=estimated_latency,
            estimated_cost=estimated_cost,
            score=total_score,
            score_breakdown=scores,
        )

    def _select_model(self, subtask: SubTask, agent: AgentProfile) -> str:
        if agent.default_model:
            return agent.default_model
        if agent.supported_models:
            return agent.supported_models[0]
        return "default"

    def _select_tools(self, subtask: SubTask, agent: AgentProfile) -> list[str]:
        return [t for t in subtask.required_tools if t in agent.tools]

    def _select_context(self, subtask: SubTask, agent: AgentProfile) -> list[str]:
        return [c for c in subtask.required_context if c in agent.context_access]

    def _decide_privacy(self, subtask: SubTask, agent: AgentProfile,
                        compute_tier: Location) -> str:
        if subtask.privacy_level == PrivacyLevel.RESTRICTED:
            return "local_only"
        if subtask.privacy_level == PrivacyLevel.CONFIDENTIAL and compute_tier == Location.CLOUD:
            return "anonymize"
        return "allow_remote"

    def _determine_execution_mode(self, subtask: SubTask, agent: AgentProfile) -> str:
        if len(subtask.required_capabilities) > 2:
            return "collaborative"
        return "direct"

    def _score_capability(self, subtask: SubTask, agent: AgentProfile) -> float:
        if not subtask.required_capabilities:
            return 0.5
        scores = []
        for req in subtask.required_capabilities:
            cap = agent.get_capability(req.capability_type)
            if cap is None:
                scores.append(0.0)
            else:
                scores.append(1.0 if cap.quality >= req.min_quality else cap.quality / req.min_quality)
        return sum(scores) / len(scores)

    def _score_model_quality(self, subtask: SubTask, model_id: str) -> float:
        model = self.model_registry.get_model(model_id)
        if not model:
            return 0.5
        return model.quality_scores.get(subtask.name, 0.5)

    def _score_tool_coverage(self, subtask: SubTask, selected_tools: list[str]) -> float:
        if not subtask.required_tools:
            return 1.0
        return len(selected_tools) / len(subtask.required_tools)

    def _score_context_relevance(self, subtask: SubTask, selected_context: list[str]) -> float:
        if not subtask.required_context:
            return 1.0
        return len(selected_context) / len(subtask.required_context)

    def _score_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        estimated = self._estimate_latency(subtask, agent)
        return max(0.0, 1.0 - estimated / 10000)

    def _score_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        estimated = self._estimate_cost(subtask, agent)
        return max(0.0, 1.0 - estimated)

    def _score_privacy(self, subtask: SubTask, agent: AgentProfile, action: str) -> float:
        if action == "local_only":
            return 1.0
        if action == "anonymize":
            return 0.7
        return 0.5

    def _estimate_latency(self, subtask: SubTask, agent: AgentProfile) -> float:
        base = agent.avg_latency_ms
        compute = subtask.estimated_computation * 0.5
        data = subtask.estimated_data_size_kb * 0.01
        network = self.network_model.get_latency(Location.TERMINAL, agent.location)
        return base + compute + data + network

    def _estimate_cost(self, subtask: SubTask, agent: AgentProfile) -> float:
        return agent.cost_per_invocation + subtask.estimated_computation * 0.001
```

#### 4.2 三个控制面

新建 `backend/control_planes/resource_control.py`：

```python
"""资源控制面."""
from __future__ import annotations
from backend.tacn.layers.l1_infrastructure.network import NetworkModel
from backend.tacn.layers.l1_infrastructure.resource_monitor import ResourceMonitor
from backend.tacn.layers.l2_terminal_agents.registry import AgentRegistry
from backend.tacn.core.models import Location


class ResourceControlPlane:
    """资源控制面.

    职责: 终端资源监测、边缘负载感知、云端资源调度、
    链路状态监测、队列估计、能耗管理、网络切片、拥塞控制.

    回答: 当前哪些资源可用？哪些资源拥塞？
    """

    def __init__(self, network_model: NetworkModel,
                 resource_monitor: ResourceMonitor,
                 agent_registry: AgentRegistry):
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
                    "count": len(self.resource_monitor.get_nodes_by_location(loc)),
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

    def estimate_end_to_end_latency(self, src: Location, dst: Location,
                                      computation_ms: float) -> float:
        """估算端到端时延."""
        network = self.network_model.get_latency(src, dst)
        return network + computation_ms
```

新建 `backend/control_planes/semantic_control.py`：

```python
"""语义与智能体控制面."""
from __future__ import annotations
from backend.tacn.core.models import Intent, AgentAssignment
from backend.tacn.layers.l2_terminal_agents.registry import AgentRegistry
from backend.tacn.layers.l2_terminal_agents.model_registry import ModelRegistry
from backend.tacn.layers.l2_terminal_agents.tool_registry import ToolRegistry
from backend.tacn.layers.l2_terminal_agents.context_registry import ContextRegistry


class SemanticControlPlane:
    """语义与智能体控制面.

    职责: 用户意图解析、任务语义识别、子任务图生成、
    智能体能力发现、能力匹配、模型/工具/上下文选择、
    多智能体协作关系管理.

    回答: 用户真正想完成什么？该任务需要哪些能力？应由哪些智能体协同完成？
    """

    def __init__(self, agent_registry: AgentRegistry,
                 model_registry: ModelRegistry,
                 tool_registry: ToolRegistry,
                 context_registry: ContextRegistry):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.context_registry = context_registry

    def discover_capabilities(self, intent: Intent) -> dict:
        """发现满足意图所需的能力."""
        available_agents = {}
        for cap_req in intent.required_capabilities:
            agents = self.agent_registry.get_agents_by_capability(cap_req.capability_type)
            available_agents[cap_req.capability_type.value] = [
                {"id": a.id, "name": a.name, "location": a.location.value,
                 "quality": next((c.quality for c in a.capabilities
                                  if c.capability_type == cap_req.capability_type), 0.0)}
                for a in agents
            ]
        return available_agents

    def get_collaboration_topology(self, assignments: list[AgentAssignment]) -> dict:
        """分析多智能体协作拓扑."""
        agents_used = set(a.agent_id for a in assignments)
        locations_used = set(a.location.value for a in assignments)
        return {
            "num_agents": len(agents_used),
            "num_locations": len(locations_used),
            "agents": list(agents_used),
            "locations": list(locations_used),
        }
```

新建 `backend/control_planes/trust_privacy_control.py`：

```python
"""信任、安全与隐私控制面."""
from __future__ import annotations
from backend.tacn.core.models import AgentProfile, PrivacyLevel, SubTask


class TrustPrivacyControlPlane:
    """信任、安全与隐私控制面.

    职责: 隐私敏感任务识别、本地数据最小化处理、数据脱敏、
    智能体身份认证、可信度评估、工具权限控制、上下文访问控制、执行审计.

    回答: 哪些数据不能离开本地？哪些智能体可信？哪些工具可以调用？
    """

    PRIVACY_ORDER = {
        PrivacyLevel.PUBLIC: 0,
        PrivacyLevel.INTERNAL: 1,
        PrivacyLevel.CONFIDENTIAL: 2,
        PrivacyLevel.RESTRICTED: 3,
    }

    def assess_privacy_risk(self, subtask: SubTask, agent: AgentProfile) -> float:
        """评估隐私风险 (0-1，越高越危险)."""
        task_level = self.PRIVACY_ORDER.get(subtask.privacy_level, 0)
        agent_level = self.PRIVACY_ORDER.get(agent.privacy_level, 0)
        if agent_level >= task_level:
            return 0.0
        return (task_level - agent_level) / 3.0

    def is_privacy_compatible(self, subtask: SubTask, agent: AgentProfile) -> bool:
        """检查隐私兼容性."""
        return self.assess_privacy_risk(subtask, agent) == 0.0

    def filter_sensitive_data(self, data: dict,
                               privacy_level: PrivacyLevel) -> dict:
        """为远程执行过滤敏感数据."""
        if privacy_level in (PrivacyLevel.RESTRICTED, PrivacyLevel.CONFIDENTIAL):
            filtered = {}
            sensitive_keys = {"user_id", "location_exact", "biometric",
                              "password", "token", "credential"}
            for k, v in data.items():
                if k not in sensitive_keys:
                    filtered[k] = v
            return filtered
        return data

    def check_tool_permission(self, agent: AgentProfile, tool_id: str,
                               required_permissions: list[str]) -> bool:
        """检查工具权限."""
        # 简化实现: 检查 agent 的 privacy_level 是否足够高
        if not required_permissions:
            return True
        agent_level = self.PRIVACY_ORDER.get(agent.privacy_level, 0)
        return agent_level >= 1  # 至少 INTERNAL

    def evaluate_trust(self, agent: AgentProfile) -> float:
        """评估智能体可信度 (基于 reliability_score)."""
        return agent.reliability_score
```

#### 4.3 集成到执行引擎

更新 `backend/orchestration/execution_engine.py`（原 `tacn_system.py`）：

```python
class TACNSystem:
    def __init__(self, registry, llm_client=None, llm_config=None,
                 routing_config=None,  # 向后兼容
                 # 新增参数
                 model_registry=None, tool_registry=None,
                 context_registry=None, network_model=None,
                 mtcc_config=None):
        ...
        # 优先使用 MTCC，否则回退到简单 Router
        if model_registry and tool_registry and context_registry:
            self.use_mtcc = True
            self.mtcc = MTCCOrchestrator(
                registry, model_registry, tool_registry,
                context_registry, network_model, mtcc_config
            )
            self.resource_control = ResourceControlPlane(...)
            self.semantic_control = SemanticControlPlane(...)
            self.trust_control = TrustPrivacyControlPlane(...)
        else:
            self.use_mtcc = False
            self.router = AgentCapabilityRouter(registry, routing_config)

    async def process_request(self, request, deadline_ms) -> ExecutionPlan:
        intent = await self.intent_parser.parse(request, deadline_ms)
        subtask_graph = await self.subtask_builder.build(intent)

        if self.use_mtcc:
            mtcc_decisions = self.mtcc.orchestrate_graph(subtask_graph)
            assignments = [self._decision_to_assignment(d) for d in mtcc_decisions]
        else:
            assignments = self.router.route_subtask_graph(subtask_graph)
        ...

    def _decision_to_assignment(self, decision: MTCCDecision) -> AgentAssignment:
        agent = self.registry.get_agent(decision.selected_agent_id)
        return AgentAssignment(
            subtask_id=decision.subtask_id,
            agent_id=decision.selected_agent_id,
            location=agent.location if agent else decision.selected_compute_tier,
            estimated_duration_ms=decision.estimated_latency_ms,
            estimated_cost=decision.estimated_cost,
        )
```

#### 4.4 验证标准

- [ ] `MTCCOrchestrator.orchestrate_subtask()` 返回包含 agent/model/tool/context/privacy_action 的完整决策
- [ ] `orchestrate_graph()` 能处理带依赖的子任务图
- [ ] 三个控制面能独立运行并返回状态信息
- [ ] `TACNSystem` 在传入完整 Registry 时使用 MTCC，否则回退到简单 Router
- [ ] MTCC 编排结果中的 `privacy_action` 对 RESTRICTED 任务返回 "local_only"

---

### 阶段五：双闭环优化 + 终端智能体差异化（P1，2-3 天）

#### 5.1 执行反馈模块

新建 `backend/orchestration/feedback.py`：

```python
"""执行反馈与闭环更新."""
from __future__ import annotations
from backend.tacn.core.models import IntentType, TaskResult, ExecutionPlan
from backend.tacn.layers.l2_terminal_agents.registry import AgentRegistry
from backend.tacn.layers.l2_terminal_agents.model_registry import ModelRegistry
from backend.tacn.layers.l2_terminal_agents.tool_registry import ToolRegistry


class ExecutionFeedback:
    """执行反馈 - 驱动双闭环优化.

    资源-能力优化环:
    资源感知 → Agent 能力建模 → MTCC 编排 → 协作执行反馈 → 资源与能力状态更新

    意图-服务优化环:
    用户意图 → 意图解析 → 任务图 → Agent 能力匹配 → 多 Agent 协作执行
    → 结果交付 → 用户反馈与服务策略更新
    """

    ALPHA = 0.1  # 指数移动平均系数

    def __init__(self, agent_registry: AgentRegistry,
                 model_registry: ModelRegistry = None,
                 tool_registry: ToolRegistry = None):
        self.agent_registry = agent_registry
        self.model_registry = model_registry
        self.tool_registry = tool_registry

    def update_after_execution(self, result: TaskResult, plan: ExecutionPlan):
        """执行后更新资源-能力状态 (资源-能力优化环).

        更新内容:
        - Agent reliability_score
        - Agent observed_latency_ms
        - Agent tool_success_rate
        - Agent context_hit_rate
        - Agent routing_score
        """
        for subtask_id, sr in result.subtask_results.items():
            if not isinstance(sr, dict):
                continue
            agent_id = sr.get("agent_id")
            agent = self.agent_registry.get_agent(agent_id)
            if agent is None:
                continue

            success = sr.get("success", False)
            actual_latency = sr.get("latency_ms", 0)

            # 更新可靠性 (指数移动平均)
            agent.reliability_score = (
                self.ALPHA * (1.0 if success else 0.0)
                + (1 - self.ALPHA) * agent.reliability_score
            )

            # 更新观测时延
            agent.observed_latency_ms = (
                self.ALPHA * actual_latency
                + (1 - self.ALPHA) * agent.observed_latency_ms
            )

            # 更新路由评分
            agent.routing_score = self._calculate_routing_score(agent)

    def update_service_policy(self, intent_type: IntentType, result: TaskResult):
        """更新服务策略 (意图-服务优化环).

        根据执行结果调整该意图类型的服务策略.
        """
        # 记录成功/失败模式，可用于后续意图解析的策略调整
        pass

    def _calculate_routing_score(self, agent) -> float:
        """计算综合路由评分."""
        return (
            0.3 * agent.reliability_score
            + 0.2 * max(0.0, 1.0 - agent.observed_latency_ms / 10000)
            + 0.2 * agent.tool_success_rate
            + 0.15 * agent.context_hit_rate
            + 0.15 * agent.get_available_capacity()
        )
```

#### 5.2 终端智能体差异化

更新四种 Agent，使其具有位置特异性行为：

**TerminalAgent** — 隐私过滤 + 本地轻量推理：

```python
# backend/agent/terminal_agent.py
class TerminalAgent(LLMAgent):
    """终端智能体.

    特有行为: 隐私过滤、本地数据最小化处理、轻量推理.
    """

    async def execute(self, subtask, context=None) -> SubTaskResult:
        # 1. 隐私过滤
        filtered_context = self._filter_sensitive_data(context)

        # 2. 执行
        result = await super().execute(subtask, filtered_context)

        # 3. 记录隐私处理
        result.metadata["privacy_filtered"] = context != filtered_context
        result.metadata["data_minimized"] = True
        return result

    def _filter_sensitive_data(self, context):
        if not context:
            return context
        sensitive_keys = {"user_id", "location_exact", "biometric",
                          "password", "token"}
        return {k: v for k, v in context.items() if k not in sensitive_keys}
```

**EdgeAgent** — 区域知识检索 + GPU 加速：

```python
# backend/agent/edge_agent.py
class EdgeAgent(LLMAgent):
    """边缘智能体.

    特有行为: 区域知识库检索、GPU 加速推理、本地上下文增强.
    """

    async def execute(self, subtask, context=None) -> SubTaskResult:
        # 边缘特有: 为 RAG 任务增强上下文
        if any(c.capability_type.value == "rag_retrieval"
               for c in subtask.required_capabilities):
            context = await self._enrich_with_local_kb(context)

        result = await super().execute(subtask, context)
        result.metadata["knowledge_enriched"] = True
        return result

    async def _enrich_with_local_kb(self, context):
        if not context:
            context = {}
        context["_edge_kb_note"] = "已从边缘知识库检索相关文档"
        return context
```

**CloudAgent** — 复杂推理 + 长上下文：

```python
# backend/agent/cloud_agent.py
class CloudAgent(LLMAgent):
    """云端智能体.

    特有行为: 复杂推理、长上下文处理、全局知识访问.
    成本系数较高.
    """

    async def execute(self, subtask, context=None) -> SubTaskResult:
        result = await super().execute(subtask, context)
        # 云端执行成本更高
        result.cost = result.cost * 1.5
        result.metadata["cloud_accelerated"] = True
        return result
```

**PeerAgent** — D2D 协作：

```python
# backend/agent/peer_agent.py
class PeerAgent(LLMAgent):
    """对等智能体.

    特有行为: D2D 通信、邻近终端协作、协同感知.
    """

    async def execute(self, subtask, context=None) -> SubTaskResult:
        result = await super().execute(subtask, context)
        result.metadata["d2d_collaboration"] = True
        return result
```

#### 5.3 验证标准

- [ ] 执行完成后 Agent 的 `reliability_score` 有更新（成功任务 > 1.0 的初始值会逐渐下降到接近实际成功率）
- [ ] TerminalAgent 的执行结果中 `privacy_filtered: True`
- [ ] EdgeAgent 的执行结果中 `knowledge_enriched: True`
- [ ] CloudAgent 的执行成本是基础成本的 1.5 倍
- [ ] 多次执行后 Agent 的 `routing_score` 随反馈变化

---

### 阶段六：实验脚本 + 测试 + 文档（P2，2-3 天）

#### 6.1 实验脚本

新建 `scripts/run_all_magazine_experiments.py`：

```python
"""运行 magazine 全量实验."""
from __future__ import annotations
import asyncio
import csv
import time
from pathlib import Path
from backend.tacn.core.config import TACNConfig
from backend.tacn.layers.l3_orchestration.execution_engine import TACNSystem
from backend.tacn.layers.l4_application.workload.generator import WorkloadGenerator
from backend.tacn.layers.l4_application.evaluation.metrics import MetricsCalculator
from backend.tacn.layers.l2_terminal_agents.registry import create_default_registry
from backend.tacn.layers.l2_terminal_agents.model_registry import create_default_model_registry
from backend.tacn.layers.l2_terminal_agents.tool_registry import create_default_tool_registry
from backend.tacn.layers.l2_terminal_agents.context_registry import create_default_context_registry
from backend.tacn.layers.l1_infrastructure.network import NetworkModel
from backend.tacn.baselines.cloud_only import CloudOnlyBaseline
from backend.tacn.baselines.resource_aware_cpn import ResourceAwareCPN
from backend.tacn.baselines.semantic_router import SemanticOnlyRouter


async def run_method(method, requests: list[str]) -> list:
    results = []
    for req in requests:
        try:
            plan = await method.process_request(req)
            result = await method.execute_plan(plan)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}")
    return results


async def main(config_path: str):
    config = TACNConfig(config_path)
    exp = config.experiment_config
    output_dir = Path(exp.get("output_dir", "outputs/magazine"))
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = WorkloadGenerator(seed=exp.get("seed", 42))
    metrics = MetricsCalculator()

    # 生成工作负载
    requests = generator.generate_mixed(exp.get("num_tasks", 100))

    # 初始化组件
    registry = create_default_registry()
    model_registry = create_default_model_registry()
    tool_registry = create_default_tool_registry()
    context_registry = create_default_context_registry()
    network_model = NetworkModel()

    # 定义方法
    methods = {
        "cloud_only": CloudOnlyBaseline(registry),
        "resource_aware_cpn": ResourceAwareCPN(registry),
        "semantic_router": SemanticOnlyRouter(registry),
        "tacn_o": TACNSystem(
            registry=registry,
            model_registry=model_registry,
            tool_registry=tool_registry,
            context_registry=context_registry,
            network_model=network_model,
        ),
    }

    # 运行实验
    all_results = {}
    for method_name, method in methods.items():
        print(f"Running {method_name}...")
        start = time.time()
        results = await run_method(method, requests)
        elapsed = time.time() - start
        m = metrics.calculate_all_metrics(results)
        m["elapsed_seconds"] = elapsed
        all_results[method_name] = m
        print(f"  {method_name}: success_rate={m['task_success_rate']:.3f}, "
              f"p95_latency={m['p95_latency_ms']:.1f}ms")

    # 输出 CSV
    csv_path = output_dir / "results" / "overall.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["method"] + list(next(iter(all_results.values())).keys()))
        writer.writeheader()
        for method_name, m in all_results.items():
            writer.writerow({"method": method_name, **m})

    print(f"Results written to {csv_path}")


if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/magazine.yaml"
    asyncio.run(main(config_path))
```

新建 `scripts/run_llm_agent_samples.py`：

```python
"""运行小样本 LLM Agent 真实调用."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from backend.tacn.layers.l3_orchestration.execution_engine import TACNSystem
from backend.tacn.layers.l2_terminal_agents.registry import create_default_registry
from backend.tacn.layers.l2_terminal_agents.model_registry import create_default_model_registry
from backend.tacn.layers.l2_terminal_agents.tool_registry import create_default_tool_registry
from backend.tacn.layers.l2_terminal_agents.context_registry import create_default_context_registry
from backend.tacn.layers.l1_infrastructure.network import NetworkModel
from backend.tacn.llm.config import LLMConfig
from backend.tacn.layers.l4_application.workload.generator import WorkloadGenerator


async def main(num_tasks: int = 8, use_real: bool = False):
    registry = create_default_registry()

    llm_config = None
    if use_real:
        llm_config = LLMConfig(
            api_key=os.getenv("TACN_API_KEY", ""),
            base_url=os.getenv("TACN_BASE_URL", ""),
            model=os.getenv("TACN_MODEL", "gpt-4o-mini"),
        )

    system = TACNSystem(
        registry=registry,
        llm_config=llm_config,
        model_registry=create_default_model_registry(),
        tool_registry=create_default_tool_registry(),
        context_registry=create_default_context_registry(),
        network_model=NetworkModel(),
    )

    generator = WorkloadGenerator(seed=42)
    requests = generator.generate_mixed(num_tasks)

    results = []
    for req in requests:
        plan = await system.process_request(req)
        result = await system.execute_plan(plan)
        results.append({
            "request": req,
            "intent_type": plan.intent.intent_type.value,
            "num_subtasks": len(plan.subtask_graph.subtasks),
            "success": result.success,
            "latency_ms": result.actual_latency_ms,
            "llm_agent_used": any(
                sr.get("metadata", {}).get("llm_called", False)
                for sr in result.subtask_results.values()
                if isinstance(sr, dict)
            ),
        })

    output_path = Path("outputs/llm_agent_samples.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Results written to {output_path}")
    print(f"LLM agents used: {sum(1 for r in results if r['llm_agent_used'])}/{len(results)}")


if __name__ == "__main__":
    import sys
    num_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    use_real = "--use-real" in sys.argv
    asyncio.run(main(num_tasks, use_real))
```

#### 6.2 测试

新建 `tests/conftest.py`：

```python
"""测试配置."""
import pytest
from backend.tacn.layers.l2_terminal_agents.registry import create_default_registry
from backend.tacn.layers.l2_terminal_agents.model_registry import create_default_model_registry
from backend.tacn.layers.l2_terminal_agents.tool_registry import create_default_tool_registry
from backend.tacn.layers.l2_terminal_agents.context_registry import create_default_context_registry
from backend.tacn.layers.l1_infrastructure.network import NetworkModel


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def model_registry():
    return create_default_model_registry()


@pytest.fixture
def tool_registry():
    return create_default_tool_registry()


@pytest.fixture
def context_registry():
    return create_default_context_registry()


@pytest.fixture
def network_model():
    return NetworkModel()
```

新建 `tests/test_intent_parser.py`：

```python
"""意图解析器测试."""
import pytest
from backend.tacn.layers.l3_orchestration.intent import LLMIntentParser


@pytest.mark.asyncio
async def test_parse_emergency_intent():
    parser = LLMIntentParser(llm_client=None)
    intent = await parser.parse("实验楼烟雾传感器报警，请结合摄像头画面判断")
    assert intent is not None
    assert intent.intent_type.value == "emergency_response"


@pytest.mark.asyncio
async def test_parse_inspection_intent():
    parser = LLMIntentParser(llm_client=None)
    intent = await parser.parse("请对A区设备进行全面巡检并生成巡检报告")
    assert intent is not None
    assert intent.intent_type.value == "robot_inspection"
```

新建 `tests/test_mtcc_orchestrator.py`：

```python
"""MTCC 编排器测试."""
import pytest
from backend.tacn.core.models import SubTask, CapabilityType, CapabilityRequirement, PrivacyLevel
from backend.tacn.layers.l3_orchestration.mtcc_orchestrator import MTCCOrchestrator, MTCCConfig


def test_mtcc_returns_complete_decision(registry, model_registry, tool_registry,
                                         context_registry, network_model):
    orchestrator = MTCCOrchestrator(
        registry, model_registry, tool_registry, context_registry, network_model
    )
    subtask = SubTask(
        name="感知异常",
        required_capabilities=[
            CapabilityRequirement(capability_type=CapabilityType.SENSING, min_quality=0.5),
        ],
        required_tools=["temperature_sensor"],
        privacy_level=PrivacyLevel.INTERNAL,
    )
    decision = orchestrator.orchestrate_subtask(subtask)
    assert decision is not None
    assert decision.selected_agent_id != ""
    assert decision.selected_model != ""
    assert decision.privacy_action in ("local_only", "anonymize", "allow_remote")
    assert decision.execution_mode in ("direct", "delegated", "collaborative")
    assert decision.score > 0


def test_mtcc_privacy_local_only_for_restricted(registry, model_registry,
                                                  tool_registry, context_registry,
                                                  network_model):
    orchestrator = MTCCOrchestrator(
        registry, model_registry, tool_registry, context_registry, network_model
    )
    subtask = SubTask(
        name="敏感数据分析",
        required_capabilities=[
            CapabilityRequirement(capability_type=CapabilityType.REASONING, min_quality=0.5),
        ],
        privacy_level=PrivacyLevel.RESTRICTED,
    )
    decision = orchestrator.orchestrate_subtask(subtask)
    if decision:
        assert decision.privacy_action == "local_only"
```

新建 `tests/test_feedback_loop.py`：

```python
"""反馈回路测试."""
from backend.tacn.core.models import TaskResult, TaskStatus, ExecutionPlan, Intent, IntentType
from backend.tacn.layers.l3_orchestration.feedback import ExecutionFeedback


def test_feedback_updates_reliability(registry):
    feedback = ExecutionFeedback(registry)
    agent = registry.get_all_agents()[0]
    initial_score = agent.reliability_score

    # 模拟成功结果
    result = TaskResult(
        task_id="test", plan_id="test", status=TaskStatus.COMPLETED,
        success=True, actual_latency_ms=100, actual_cost=0.01,
        subtask_results={
            "st1": {"agent_id": agent.id, "success": True, "latency_ms": 100},
        },
    )
    plan = ExecutionPlan(
        task_id="test", intent=Intent(text="test", intent_type=IntentType.EMERGENCY_RESPONSE),
        subtask_graph=None,
    )

    feedback.update_after_execution(result, plan)
    # reliability_score 应该通过 EMA 更新
    assert agent.reliability_score != initial_score or agent.reliability_score == 1.0
```

新建 `tests/test_tacn_system.py`：

```python
"""TACN 系统集成测试."""
import pytest
from backend.tacn.layers.l3_orchestration.execution_engine import TACNSystem
from backend.tacn.layers.l2_terminal_agents.registry import create_default_registry


@pytest.mark.asyncio
async def test_full_pipeline():
    registry = create_default_registry()
    system = TACNSystem(registry=registry)
    plan = await system.process_request("实验楼烟雾传感器报警，请结合摄像头画面判断")
    assert plan is not None
    assert len(plan.subtask_graph.subtasks) > 0
    assert len(plan.assignments) > 0
```

#### 6.3 文档

新建 `docs/tacn_project_outline.md`（项目概念基准）和 `docs/experiment_positioning.md`（实验定位）。内容参照 README 第 1-7 节的理论描述。

#### 6.4 输出目录

```bash
mkdir -p outputs/default
mkdir -p outputs/magazine/results
mkdir -p outputs/magazine/traces
mkdir -p outputs/magazine/figures
mkdir -p outputs/magazine/reports
# 在 outputs/ 下添加 .gitkeep 文件以保留目录结构
```

#### 6.5 验证标准

- [ ] `python scripts/run_all_magazine_experiments.py --config configs/magazine.yaml` 跑完全部实验
- [ ] 输出 CSV 到 `outputs/magazine/results/overall.csv`
- [ ] `pytest tests/` 全部通过
- [ ] `python scripts/run_llm_agent_samples.py --num-tasks 8` 能运行（mock 模式）
- [ ] `python main.py run --config configs/default.yaml` 能运行完整实验流水线

---

## 四、实施优先级与工作量估计

| 阶段 | 优先级 | 预估工作量 | 依赖 | 核心产出 |
|---|---|---|---|---|
| 阶段一：目录重组 + Bug 修复 | **P0** | 2-3 天 | 无 | 四层目录结构、import 修正、bug 修复 |
| 阶段二：配置系统 + L1 | **P1** | 2 天 | 阶段一 | YAML 配置、NetworkModel、CLI 入口 |
| 阶段三：L2 Registry + AgentRuntime | **P1** | 2-3 天 | 阶段一 | Model/Tool/Context Registry、增强 AgentProfile、AgentRuntime 接口 |
| 阶段四：MTCC + 控制面 | **P0** | 3-4 天 | 阶段二、三 | MTCCOrchestrator、三控制面 |
| 阶段五：闭环反馈 + Agent 差异化 | **P1** | 2-3 天 | 阶段四 | ExecutionFeedback、四种 Agent 差异化 |
| 阶段六：实验脚本 + 测试 | **P2** | 2-3 天 | 阶段五 | 实验流水线、测试、文档 |

**总计：约 13-18 天**

阶段一到三是基础，可并行推进；阶段四是核心创新点；阶段五和六是完善。

---

## 五、与 README 的对应关系检查清单

| README 章节 | 对应实现 | 阶段 |
|---|---|---|
| 1. TACN 项目定位 | README 准确，代码结构需重组 | 阶段一 |
| 2. 背景与动机 | 概念文档，无需代码 | — |
| 3. TACN 核心定义 | 数据模型 (`models.py`) | 阶段三扩充 |
| 4. 核心范式转变 | MTCC 编排器 | 阶段四 |
| 5. 核心问题 | 各模块分别解决 | 阶段四 |
| 6. 总体架构 | 四层目录 + 控制面 | 阶段一 + 四 |
| 7. 工作流程 | 执行引擎 | 阶段一迁移 + 四重构 |
| 8. 原型定位 | README 准确 | — |
| 9. 核心模块映射 | 目录重组后对齐 | 阶段一 |
| 10. 快速开始 | CLI 入口 + 配置 | 阶段二 |
| 11. OpenAI API | LLM 客户端 + .env | 阶段二 |
| 12. 项目结构 | 目录重组 | 阶段一 |
| 13. 实验任务与指标 | Workload + Metrics + 实验脚本 | 阶段六 |
| 14. 设计原则 | MTCC + 反馈 + 能力画像 | 阶段四 + 五 |
| 15. 表述边界 | 无需代码 | — |
| 16. 应用场景 | 场景适配器 | 阶段二 (config) + 可选 L4 scenarios |
| 17. 核心创新 | MTCC + 双闭环 + 终端智能体 | 阶段四 + 五 |
