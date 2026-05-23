# TACN-Proto: Terminal Agent Computing Network

> 面向未来 5G-A/6G 的终端智能体算力网络原型
> 从资源驱动的任务卸载，走向意图驱动的智能体能力编排

TACN-Proto 是一个面向论文实验和体系验证的轻量级原型，用于验证 **TACN（Terminal Agent Computing Network，终端智能体算力网络）** 的核心思想：将终端、边缘和云端组织为可感知、可发现、可调度、可协作的智能体网络，并围绕复杂用户意图联合编排智能体、模型、工具、上下文、算力资源和网络资源。

TACN 不是智慧工厂、智慧园区或智慧医院的专用系统。这些只是可用于实验和展示的应用实例。TACN 的核心定位是一个通用的 agent-native computing fabric：让未来网络从“连接设备、调度算力”的系统，升级为“理解意图、编排能力、协同智能体”的系统。

项目概念基准见 [`docs/tacn_project_outline.md`](docs/tacn_project_outline.md)，实验定位见 [`docs/experiment_positioning.md`](docs/experiment_positioning.md)。修改代码前应先阅读这两份文档和相关实现文件，确保变化仍服务于 TACN 主链路：

```text
complex intent
-> intent parsing
-> subtask graph
-> agent capability matching
-> model-tool-compute-context orchestration
-> execution
```

## 1. TACN 项目定位

TACN 的目标不是简单判断“任务应该在本地、边缘还是云端执行”，而是面向未来网络中的复杂智能服务，研究如何将用户意图解析为结构化任务，并在终端、邻近终端、边缘和云端之间联合编排：

- 智能体；
- 模型；
- 工具；
- 上下文；
- 算力资源；
- 网络资源；
- 隐私与安全约束。

TACN 的核心问题是：

> 面向复杂用户意图，如何通过终端智能体、边缘智能体和云端智能体的协同，完成意图解析、任务拆解、能力匹配、联合编排和反馈优化。

因此，TACN 的本质是：

> 从资源驱动的任务卸载网络，升级为意图驱动的智能体能力编排网络。

## 2. 背景与动机

传统网络中的终端主要承担数据采集、业务请求发起、通信接入和结果接收。复杂推理、全局决策和业务编排通常由边缘或云端完成，终端被视为被动设备或任务源。

随着端侧计算、边缘智能、轻量化大模型、多模态感知和智能体技术的发展，手机、摄像头、传感器、机器人、AR 眼镜、车载终端、可穿戴设备等终端正在逐渐具备：

- 环境感知能力；
- 本地数据处理能力；
- 轻量模型推理能力；
- 局部任务决策能力；
- 工具调用能力；
- 上下文管理能力；
- 隐私过滤能力；
- 与邻近终端协作的能力。

这意味着，终端正在从传统 device 演进为具备一定自治能力的 **Terminal Agent**。

与此同时，网络承载的任务也不再只是单一计算任务。未来智能服务通常包含意图理解、任务拆解、多模型协同、工具调用、上下文检索、多智能体协作、隐私约束、安全约束、实时性约束和用户反馈优化。传统任务卸载、资源调度和边缘推理机制很难完整表达这类服务的执行过程。

TACN 正是在这一背景下提出：它希望将终端、边缘和云端的智能体能力组织成一个可感知、可调度、可协作、可反馈优化的新型算力网络。

## 3. TACN 核心定义

TACN 是一种以终端智能体为原生主体的智能化算力网络。它将分布式终端、边缘节点和云端平台抽象为可管理、可发现、可调度的智能体集合，并通过意图解析、任务图生成、智能体能力匹配和模型-工具-算力-上下文联合编排，实现复杂智能服务的协同执行。

TACN 可以抽象为：

```math
\mathcal{N}^{\mathrm{TACN}}
=
\left(
\mathcal{A},
\mathcal{M},
\mathcal{U},
\mathcal{C},
\mathcal{R},
\mathcal{I}
\right)
```

其中，$\mathcal{A}$ 表示智能体集合，$\mathcal{M}$ 表示模型集合，$\mathcal{U}$ 表示工具集合，$\mathcal{C}$ 表示上下文集合，$\mathcal{R}$ 表示资源状态集合，$\mathcal{I}$ 表示用户意图或任务集合。

一个 TACN 系统主要由以下要素组成：

| 要素 | 含义 |
| --- | --- |
| Terminal Agent | 具备感知、推理、工具调用和协作能力的终端智能体 |
| Edge Agent | 部署在边缘侧，负责区域级推理、检索、融合和编排的智能体 |
| Cloud Agent | 部署在云端，负责复杂推理、长上下文处理和全局知识服务的智能体 |
| Model | 支撑任务推理的模型，包括轻量模型、视觉模型、RAG 模型和大模型 |
| Tool | 可被智能体调用的外部工具、API、设备控制接口或业务系统 |
| Context | 与任务相关的用户上下文、环境上下文、设备状态、历史记录和知识库 |
| Compute | 终端、邻近终端、边缘和云端提供的计算资源 |
| Network | 支撑智能体协作的通信、路由、切片和连接能力 |
| Policy | 资源调度、隐私保护、安全控制和服务优化策略 |

TACN 的核心不是单一模块，而是一种系统范式：将终端设备提升为终端智能体，并通过网络化方式组织智能体能力，使未来网络能够围绕复杂意图进行协同感知、协同推理、协同执行和持续优化。

## 4. 核心范式转变

TACN 相比传统端侧算力网络，主要体现三类转变。

| 转变 | 传统网络 | TACN |
| --- | --- | --- |
| 设备中心 -> 智能体中心 | 终端主要负责数据采集和通信接入 | 终端参与任务理解、局部推理、上下文维护和协作执行 |
| 资源调度 -> 能力编排 | 调度 CPU、GPU、内存、带宽和存储 | 调度视觉理解、传感器分析、RAG 检索、安全推理、工具调用、多智能体协作等能力 |
| 任务卸载 -> 意图编排 | `task -> local / edge / cloud` | `complex intent -> intent parsing -> subtask graph -> agent capability matching -> model-tool-compute-context orchestration -> collaborative execution -> feedback optimization` |

TACN 的调度逻辑不是简单选择“哪个节点资源最多”，而是选择“哪些智能体、模型、工具和上下文最适合协作完成当前意图”。

## 5. TACN 要解决的核心问题

TACN 面向复杂智能服务，需要解决以下关键问题。

| 问题 | TACN 中的含义 |
| --- | --- |
| 复杂意图如何被网络理解 | 从自然语言请求、应用请求、传感事件或多模态输入中识别真实目标 |
| 复杂任务如何被拆解 | 将复杂意图转换为带依赖关系、可并行关系和工具/上下文需求的子任务图 |
| 智能体能力如何被建模 | 维护包含 capability、model、tool、context、latency、cost、privacy risk、reliability、load 的能力画像 |
| 智能体如何被匹配和调度 | 综合能力覆盖、模型适配、工具可用、上下文访问、资源状态、网络时延、成本、隐私风险和截止期选择执行者 |
| 多智能体如何协作执行 | 支持子任务分配、中间结果传递、上下文共享、工具协同、状态同步、失败回退和结果聚合 |
| 如何实现 MTCC 联合编排 | 对模型、工具、算力和上下文进行联合选择，而不是只决定执行位置 |

其中，**Model-Tool-Compute-Context Co-Orchestration（MTCC）** 是 TACN 的关键创新之一。它为每个子任务同时决定 selected agent、selected model、selected tool、selected context、selected compute tier、privacy action 和 execution mode。

## 6. 总体架构

TACN 的总体架构可以概括为：

> 四层架构 + 三个控制面 + 双闭环优化

### 6.1 四层架构

| 层级 | 名称 | 作用 |
| --- | --- | --- |
| L1 | 端-网-边-云基础设施层 | 提供通信、计算、感知、存储和执行环境，包括终端设备、邻近终端、无线接入网络、D2D/sidelink、边缘节点、云端平台、工具接口和数据源 |
| L2 | 智能体资源与能力抽象层 | 将异构设备和节点抽象为可管理、可发现、可调度的智能体资源，维护 Agent Registry、Capability Profile、Model Registry、Tool Registry、Context Registry 和资源状态 |
| L3 | 意图感知的智能体编排与协作层 | 将复杂用户意图转化为可执行的多智能体协作计划，完成意图解析、子任务图生成、能力匹配、MTCC 编排、调度、监控和反馈适配 |
| L4 | 智能服务与应用层 | 承载面向用户和业务的复杂智能服务，负责意图入口、业务接口、结果解释、用户反馈和服务策略更新 |

L3 是 TACN 的核心层。它的典型处理链路是：

```text
user request
-> parsed intent
-> subtask graph
-> agent capability matching
-> execution plan
-> collaborative execution
```

### 6.2 三个控制面

三个控制面贯穿 TACN 的四层架构。

| 控制面 | 主要职责 | 回答的问题 |
| --- | --- | --- |
| 资源控制面 | 终端资源监测、边缘负载感知、云端资源调度、链路状态监测、队列估计、能耗管理、网络切片、拥塞控制 | 当前哪些资源可用？哪些资源拥塞？任务如何获得足够的网络和计算支撑？ |
| 语义与智能体控制面 | 用户意图解析、任务语义识别、子任务图生成、智能体能力发现、能力匹配、模型/工具/上下文选择、多智能体协作关系管理 | 用户真正想完成什么？该任务需要哪些能力？应由哪些智能体协同完成？ |
| 信任、安全与隐私控制面 | 隐私敏感任务识别、本地数据最小化处理、数据脱敏、智能体身份认证、可信度评估、工具权限控制、上下文访问控制、执行审计 | 哪些数据不能离开本地？哪些智能体可信？哪些工具可以调用？执行结果是否可靠？ |

在 TACN 中，隐私与安全不是附加模块，而是影响智能体选择、模型选择、上下文访问和执行位置的重要约束。

### 6.3 双闭环优化

TACN 包含两个相互耦合的闭环优化过程。

资源-能力优化环关注系统执行效率与智能体能力画像：

```text
资源感知
-> Agent 能力建模
-> 模型-工具-算力-上下文编排
-> 协作执行反馈
-> 资源与能力状态更新
```

意图-服务优化环关注意图理解和服务质量：

```text
用户意图
-> 意图解析
-> 任务图生成
-> Agent 能力匹配
-> 多 Agent 协作执行
-> 结果交付
-> 用户反馈与服务策略更新
```

两个闭环在 Agent 选择、编排调度、协作执行、执行反馈和用户反馈处耦合。可以概括为：

> 意图环决定“要完成什么、由谁协作完成”；资源环决定“如何高效、可靠、安全地完成”。

## 7. TACN 工作流程

TACN 的典型工作流程如下：

```text
User / Application Request
      ↓
Intent Parsing
      ↓
Structured Intent
      ↓
Subtask Graph Generation
      ↓
Agent Capability Discovery
      ↓
Agent Capability Matching
      ↓
Model-Tool-Compute-Context Orchestration
      ↓
Collaborative Execution
      ↓
Result Delivery
      ↓
Execution Feedback
      ↓
Resource and Service Policy Update
```

该流程体现了 TACN 的完整链路：从用户或应用请求中识别复杂意图，将意图转换为结构化任务表示，构建子任务图，发现并匹配智能体能力，联合选择模型、工具、上下文和计算位置，组织多智能体协作执行，交付结果，并持续更新资源状态、能力画像和服务策略。

## 8. TACN-Proto 原型定位

TACN-Proto 是用于验证 TACN 核心思想的轻量级实验原型。它不声称实现完整真实的商用终端智能体算力网络，而是验证以下问题：

- 复杂用户意图是否可以被解析为结构化任务表示；
- 复杂任务是否可以被转换为子任务图；
- 子任务是否可以根据能力需求匹配到合适智能体；
- 模型、工具、算力和上下文是否可以被联合编排；
- 多智能体协作执行是否可以被记录、评估和反馈；
- TACN 是否能在任务成功率、尾部时延、隐私保护和成本之间取得更优折中。

当前原型支持：

- 生成终端智能体复杂任务负载；
- 模拟 local / peer / edge / cloud 等异构执行实体；
- 维护通用 TACN core catalog 和场景实例 catalog；
- 实现 cloud-only、resource-aware CPN、LLM semantic router、TACN-O 等比较方法；
- 实现 TACN-Orchestrator（TACN-O）和关键消融项；
- 输出 CSV 结果、汇总表、trace、报告和论文可用图；
- 可选接入 OpenAI-compatible 模型 API，用于小样本真实 LLM Agent 证据。

`configs/config.yaml` 是集中配置入口。`tacn_core` 维护场景无关的 TACN 核心能力：意图模板、复杂任务 DAG 模板、终端/边缘/云 AgentProfile、能力词表和通用任务族；`scenario_catalog` 只维护智能校园、智能工厂、智慧医院等应用场景实例。应用场景只是 TACN 的适配器，不定义 TACN 的完整 Agent 能力边界。

## 9. 核心模块与代码映射

TACN-Proto 的后端实现位于 `backend/`，采用扁平包结构。四层架构（L1-L4）的逻辑分层通过代码的 import 依赖和模块职责划分来表达，而非目录前缀。

| TACN 模块 | 作用 | 主要实现位置 |
| --- | --- | --- |
| Complex Workload Generator | 生成复杂终端智能体任务负载 | `backend/workload/generator.py` |
| Intent Parser | 将请求解析为结构化意图 | `backend/parser/intent_parser.py` |
| Subtask Graph Builder | 将复杂意图转换为子任务图 | `backend/parser/subtask_builder.py` |
| Agent Registry | 维护智能体能力画像 | `backend/registry/agent_registry.py` |
| Agent Capability Router | 根据子任务需求和资源状态匹配智能体 | `backend/router/capability_router.py` |
| Orchestration Engine | 编排引擎，协调意图解析→子任务→路由→执行 | `backend/orchestration/engine.py` |
| TACN System | 完整 TACN 流水线（LLM 驱动） | `backend/orchestration/tacn_system.py` |
| Agent Collaboration / Bus | 记录多智能体消息、重试、回退和结果传递 | `backend/agent/message.py` |
| Simulation Executor | 仿真实验执行器 | `backend/simulation/simulation.py` |
| Evaluation Metrics | 统计指标计算 | `backend/evaluation/metrics.py` |
| Baselines | 对比方法（Cloud-Only、CPN、Semantic Router） | `backend/baselines/` |
| LLM Client | OpenAI-compatible 模型接入 | `backend/llm/` |
| FastAPI API | REST API 入口 | `backend/api/` 和 `backend/main.py` |

## 10. 快速开始

```bash
cd tacn_impl
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

默认不需要 API key，先运行演示脚本验证核心流程：

```bash
python examples/demo.py              # 单请求 + 批量实验 + 意图类型演示
python examples/demo_tacn.py         # 完整 TACN 流水线演示（LLM 驱动）
python examples/demo_agent.py        # Agent 执行演示
python examples/demo_multi_agent.py  # 多层级 Agent 演示
```

启动 FastAPI 服务和前端：

```bash
cd backend && uvicorn main:app --reload --port 8000
# 然后打开 frontend/index.html
```

API 端点：

- `POST /api/tasks/process` — 处理用户请求，返回执行计划
- `POST /api/tasks/execute` — 执行已生成的计划
- `POST /api/experiments/run` — 运行对比实验
- `GET /api/agents` — 获取所有 Agent 信息

## 11. 使用 OpenAI-compatible API

请把 key 写入 `.env`，不要写进代码、README 或实验日志，不要提交到 Git。

```env
TACN_API_KEY=填入你的key
TACN_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
TACN_MODEL=gpt-4o-mini
TACN_USE_REAL_LLM=false
```

第一版建议保持：

```env
TACN_USE_REAL_LLM=false
```

原因是仿真实验更稳定、更便宜、更容易复现。等实验框架稳定后，再把部分任务切换为真实 API 调用。

## 12. 项目结构

```text
tacn_impl/
├── pyproject.toml             # Python 项目配置
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
├── backend/
│   ├── main.py                # FastAPI 应用入口
│   ├── core/
│   │   └── models.py          # 核心数据模型（Intent、SubTask、AgentProfile 等）
│   ├── parser/
│   │   ├── intent_parser.py   # 意图解析器（LLM tool-calling + 关键词回退）
│   │   ├── subtask_builder.py # 子任务图构建器（LLM + 模板回退）
│   │   ├── validators.py      # Pydantic 输出验证
│   │   └── json_repair.py     # LLM JSON 输出修复
│   ├── registry/
│   │   └── agent_registry.py  # 智能体注册表（按 location/capability 索引）
│   ├── router/
│   │   └── capability_router.py # 能力路由器（多准则打分）
│   ├── orchestration/
│   │   ├── engine.py          # 编排引擎（同步接口）
│   │   └── tacn_system.py     # TACN 完整流水线（LLM 驱动，异步）
│   ├── agent/
│   │   ├── base.py            # BaseAgent 抽象基类
│   │   ├── llm_agent.py       # LLMAgent（LLM 驱动的智能体）
│   │   ├── terminal_agent.py  # 终端智能体
│   │   ├── peer_agent.py      # 对等智能体
│   │   ├── edge_agent.py      # 边缘智能体
│   │   ├── cloud_agent.py     # 云端智能体
│   │   ├── factory.py         # AgentFactory / AgentManager
│   │   ├── message.py         # MessageBus（pub/sub 消息总线）
│   │   └── tools.py           # Agent 工具（传感器、摄像头等）
│   ├── baselines/
│   │   ├── cloud_only.py      # Cloud-Only 基线
│   │   ├── resource_aware_cpn.py # Resource-Aware CPN 基线
│   │   └── semantic_router.py # Semantic Router 基线
│   ├── simulation/
│   │   └── simulation.py      # 仿真实验执行器
│   ├── evaluation/
│   │   └── metrics.py         # 评估指标计算
│   ├── workload/
│   │   └── generator.py       # 工作负载生成器
│   ├── llm/
│   │   ├── client.py          # OpenAI-compatible LLM 客户端
│   │   └── config.py          # LLM 配置
│   └── api/
│       ├── tasks.py           # 任务处理 API
│       ├── agents.py          # Agent 管理 API
│       └── experiments.py     # 实验 API
├── frontend/
│   ├── index.html             # Web 前端（HTML + Chart.js）
│   ├── css/style.css
│   └── js/
├── examples/
│   ├── demo.py                # 综合演示
│   ├── demo_tacn.py           # TACN 完整流水线演示
│   ├── demo_agent.py          # Agent 执行演示
│   ├── demo_multi_agent.py    # 多层级 Agent 演示
│   └── demo_agent_communication.py # Agent 通信演示
└── docs/
    ├── tacn_project_outline.md    # 项目概念基准
    ├── experiment_positioning.md  # 实验定位
    └── tacn_alignment_plan.md     # 代码对齐重构方案
```

## 13. 实验任务与评价指标

为了体现 TACN 的复杂意图和多智能体协作特征，实验任务应避免退化为简单问答或单节点推理。当前原型以通用任务族建模，并通过场景适配器实例化。

| 通用任务族 | 关注能力 |
| --- | --- |
| `event_response` | 低时延、隐私、安全推理、工具调用、多智能体协作 |
| `mobile_inspection` | 传感器分析、设备查询、维护记录、路径规划 |
| `collaborative_perception` | 多终端感知、多模态融合、风险判断 |
| `context_aware_decision` | RAG 检索、设备日志、规则推理、决策支持 |
| `personal_assistant_service` | 日程、通知、用户上下文、隐私过滤、工具调用 |

核心评价指标包括：

| 指标 | 含义 |
| --- | --- |
| Task Success Rate | 复杂任务成功完成比例 |
| P95 Latency | 尾部任务时延 |
| Intent Parsing Accuracy | 意图解析准确率 |
| Capability Matching Accuracy | 智能体能力匹配准确率 |
| Agent Assignment Success Rate | 智能体分配成功率 |
| Privacy Preservation Ratio | 隐私保护比例 |
| Cloud Offloading Ratio | 云端参与比例 |
| Cost Efficiency | 成本效率 |
| Tool Success Rate | 工具调用成功率 |
| Context Hit Rate | 上下文命中率 |

推荐实验主线：

1. 系统架构对比：cloud-only、resource-aware CPN、LLM semantic router、TACN-O。
2. 意图解析质量及其对下游编排的影响。
3. 负载敏感性：改变 `arrival_rate`。
4. 消融实验：去掉 LLM intent、capability matching、resource awareness、tool-context awareness、terminal agents。

## 14. 设计原则

TACN-Proto 的实现应遵循以下原则：

- 以 TACN 机制验证为核心，重点体现意图解析、子任务图生成、Agent 能力匹配、MTCC 联合编排、多智能体协作执行和反馈驱动优化。
- 以终端智能体为主线，明确体现本地隐私过滤、本地事件初筛、本地轻量推理、邻近终端协作、机器人或 AR 终端现场执行等能力。
- 以能力画像而非单纯资源画像进行调度，Agent Registry 不应只记录算力和时延，还应记录 capability、model、tool、context、privacy risk、reliability 和 current load。
- 以 MTCC 联合编排体现创新，每个子任务都应记录 selected agent、selected model、selected tool、selected context、selected compute tier、privacy action 和 execution result。
- 以轻量闭环更新增强可信度，根据执行反馈更新 Agent reliability、observed latency、resource load、tool success rate、context hit rate、privacy risk estimate 和 routing score。

## 15. 表述边界

TACN-Proto 应被表述为轻量级实验原型，而不是完整商用系统。

推荐表述：

> This prototype validates the feasibility of intent-aware agentic capability orchestration in TACN.

推荐中文表述：

> 本项目构建了一个轻量级 TACN 原型，用于验证复杂意图解析、子任务图生成、智能体能力匹配和模型-工具-算力-上下文联合编排的可行性。

不推荐表述：

> This system fully implements a real-world terminal agent computing network.

如果没有使用真实 LLM API，不应声称系统评估了开放域自然语言理解能力。推荐表述为：

> This experiment uses reproducible rule parsing and templated workload generation to validate the system relationship among intent parsing, subtask construction, capability matching, and resource-aware orchestration in the TACN architecture, rather than evaluating general-purpose LLM understanding.

## 16. 应用场景示例

TACN 是通用的终端智能体算力网络架构，而不是面向单一应用场景的专用系统。以下场景只用于说明其应用价值，场景适配器不定义 TACN 的能力边界。

### 16.1 智慧园区应急响应

TACN 可以联合传感器智能体、摄像头智能体、边缘安全智能体、RAG 智能体和工具智能体，完成事件确认、风险判断、安全规则检索和通知执行。该场景体现多终端感知、低时延协作、隐私保护、安全规则推理和工具调用。

### 16.2 智慧工厂智能运维

在智慧工厂中，TACN 可以将产线传感器、工业相机、移动巡检机器人、PLC/设备网关、边缘视觉智能体、边缘 RAG 智能体和云端推理智能体组织为协作网络。面对“产线 A 温度和振动异常，请结合相机画面、维护记录和安全规范判断是否需要降速或停机”的复杂意图，TACN 可以完成传感事件验证、视觉确认、维护记录检索、安全策略推理、停机/降速决策和工单/通知工具调用。

该场景体现：

- 工业终端智能体从数据源升级为协作执行者；
- 设备维护知识、实时状态和安全规范共同进入上下文编排；
- 工具调用可以连接 PLC、工单系统、通知系统和质量追踪系统；
- 隐私、安全和生产连续性约束会影响 Agent 选择和执行位置；
- 智慧工厂只是 TACN 的一个应用适配器，不是 TACN 的定义边界。

### 16.3 巡检机器人协同诊断

机器人智能体可以与边缘传感器智能体、设备状态工具智能体和维护知识智能体协作，完成异常检测、设备查询、风险判断和处理建议生成。该场景体现移动终端智能体、工具调用、上下文检索、边缘侧推理和协作执行。

### 16.4 多摄像头协同安防

多个摄像头智能体可以与边缘视觉智能体和协作智能体配合，完成目标识别、轨迹跟踪、结果融合和风险判断。该场景体现多终端视觉融合、边缘协同推理、多智能体结果聚合和隐私敏感数据本地处理。

### 16.5 个人智能助手服务

用户终端智能体可以联合日程工具、地图工具、位置上下文和通知工具，完成日程理解、路线规划、会议摘要和服务提醒。该场景体现用户意图理解、工具调用、上下文感知、隐私过滤和个性化服务交付。

## 17. 核心创新总结

| 创新点 | 含义 |
| --- | --- |
| Terminal-agent-native networking | 将终端设备提升为可协作的终端智能体 |
| Intent-aware orchestration | 从复杂意图出发进行任务解析和服务编排 |
| Agentic capability networking | 将网络化对象从算力资源扩展为智能体能力 |
| MTCC co-orchestration | 联合编排模型、工具、算力和上下文 |
| Dual closed-loop optimization | 同时优化资源-能力状态和意图-服务策略 |

一句话总结：

> TACN 是面向未来 5G-A/6G 的终端智能体算力网络。它将终端设备提升为可协作的终端智能体，并通过复杂意图解析、子任务图生成、智能体能力匹配和模型-工具-算力-上下文联合编排，使网络从“资源调度系统”演进为“智能体能力协作系统”。
