# TACN：从任务卸载到网络级智能体编排

> **TACN，Terminal Agent Computing Network，终端智能体算力网络**，是面向 5G-A/6G 智能网络的一种通用网络化智能服务架构。它以复杂意图为输入，以智能体能力为调度对象，以模型—工具—算力—上下文联合编排为核心机制，实现终端、边缘和云端智能体的网络化协同服务。

## 项目启动教程
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
http://localhost:8000

---

## 1. TACN 的提出背景

随着大模型、端侧 AI、边缘计算、智能终端和 5G-A/6G 网络的发展，终端设备正在从传统的**数据采集设备**、**任务发起设备**和**算力节点**，逐步演化为具备感知、理解、推理、工具调用、上下文访问和协作执行能力的**终端智能体**。

传统网络主要解决的是连接问题和资源调度问题。例如：

- 如何连接终端设备；
- 如何传输数据；
- 如何将任务卸载到边缘或云端；
- 如何调度 CPU、GPU、带宽和存储资源；
- 如何降低任务执行时延和能耗。

但是，未来智能网络面对的任务形态正在发生变化。用户或终端发起的任务不再只是简单的计算任务，而往往是一个包含复杂意图、多个子任务、多种工具、多类上下文和多智能体协作关系的复杂服务请求。

传统 MEC、CPN 和 Edge AI 系统通常把任务抽象为：

```text
数据量 + 计算量 + 时延约束 + 资源需求
```

而终端智能体时代的复杂任务更接近：

```text
用户意图 + 子任务依赖 + 智能体能力需求 + 模型需求 + 工具需求 + 上下文需求 + 隐私约束 + 截止期约束 + 多智能体协作关系
```

因此，未来网络不能只解决"任务在哪里计算"的问题，还需要进一步解决：

> **复杂用户意图如何被理解、拆解、匹配、编排，并由分布式终端、边缘和云端智能体协同完成。**

这正是 **Terminal Agent Computing Network，TACN，终端智能体算力网络** 的提出背景。

---

## 2. 现有 Agent 已经具备内部执行流程

在定义 TACN 之前，必须先明确一个重要事实：当前主流 Agent 系统已经不是简单的大模型问答接口，而是具备内部执行流程的 Agent Runtime。

例如，OpenAI Agents SDK 将 Agent 定义为带有 instructions、tools 以及 handoffs、guardrails、structured outputs 等运行时行为的大语言模型；其工具机制允许 Agent 获取数据、运行代码、调用外部 API，甚至使用计算机等外部能力。OpenAI Agents SDK 还支持 handoff，即一个 Agent 可以把任务委派给另一个专门 Agent；其 tracing 机制会记录 LLM generation、tool call、handoff、guardrail 等运行事件。

Claude Agent SDK 也具有类似定位。Anthropic 文档说明，Claude Agent SDK 提供支撑 Claude Code 的 tools、agent loop 和 context management，使 Agent 能够读取文件、运行命令、搜索 Web、编辑代码等。Claude 的工具调用机制也支持将 Claude 连接到外部工具和 API，由 Claude 根据用户请求和工具描述决定何时调用工具。

因此，现代 Agent 通常已经具备如下微观执行流程：

```text
User Request
    |
Intent Understanding
    |
Task Planning
    |
Tool / Memory / Context Selection
    |
Action Execution
    |
Observation
    |
Reflection / Replanning
    |
Final Response or Handoff
```

这个流程可以称为：

> **Micro-agent workflow，即单个智能体内部工作流。**

它关注的是：

- 单个 Agent 如何理解任务；
- 单个 Agent 如何规划步骤；
- 单个 Agent 如何调用工具；
- 单个 Agent 如何读取上下文；
- 单个 Agent 如何根据工具返回结果继续推理；
- 单个 Agent 如何完成最终输出或 handoff。

因此，TACN 不能被简单表述为"设计一个会规划、会调用工具、会执行任务的 Agent"。这一部分已经是现有 Agent 框架的重要能力。

TACN 应该站在更高层级，关注的是：

> **当大量异构 Agent 分布在终端、边缘和云端之后，网络如何发现、组织、匹配、调度和协同这些 Agent。**

---

## 3. TACN 的基本定义

**Terminal Agent Computing Network，TACN，终端智能体算力网络**，是一种面向 5G-A/6G 智能网络的**通用网络化智能服务架构**。

它将手机、摄像头、机器人、传感器、AR 眼镜、车载终端、工业设备、可穿戴设备、无人机等终端，从传统的数据源、任务源或算力节点，升级为具备感知、理解、推理、工具调用、上下文访问和协作执行能力的**终端智能体**。

TACN 通过网络级控制平面对终端智能体、边缘智能体和云端智能体进行统一发现、匹配、调度和协同，从而在时延、隐私、成本和资源约束下完成复杂用户意图。

更简洁地说：

> **TACN 不是简单决定任务在本地、边缘还是云端执行，而是围绕复杂用户意图，联合编排智能体、模型、工具、算力、上下文和网络资源，使端—边—云分布式智能体能够协同完成复杂任务。**

传统算力网络关注：

```text
任务应该在哪里计算？
```

TACN 进一步关注：

```text
用户到底想完成什么？
这个意图需要哪些能力？
需要哪些模型、工具和上下文？
由哪些终端、边缘和云端 Agent 协作？
在什么位置执行才能同时满足时延、隐私、成本和资源约束？
```

因此，TACN 的本质不是单纯的 computing offloading network，而是：

> **intent-driven agentic computing network，即意图驱动的智能体算力网络。**

---

## 4. TACN 的核心定位

TACN 的核心定位可以概括为：

> **现有 Agent 框架解决的是"单个 Agent 如何完成任务"，TACN 解决的是"网络中大量分布式 Agent 如何被组织起来完成复杂意图"。**

二者不是替代关系，而是分层关系。

| 层级 | 名称 | 关注对象 | 核心问题 |
| --- | --- | --- | --- |
| 第一层 | Model Layer | 大模型 / 小模型 | 模型如何理解、推理和生成 |
| 第二层 | Agent Runtime Layer | 单个 Agent | Agent 如何规划、调用工具、管理上下文和执行任务 |
| 第三层 | TACN Layer | 分布式终端、边缘、云端 Agent 网络 | 多个异构 Agent 如何被发现、选择、组合、调度和协同 |

可以进一步概括为：

```text
LLM 是智能内核
Agent 是具备执行流程的智能体
TACN 是连接和编排大量分布式 Agent 的网络系统
```

因此，TACN 不应与 OpenAI Agent、Claude Agent、LangGraph、AutoGen 等系统竞争"谁更会做 Agent 内部流程"。TACN 应该解决的是一个更偏网络和系统架构的问题：

> **如何把广泛分布在端、边、云的智能体组织成可发现、可匹配、可调度、可协同的网络化智能资源体系。**

---

## 5. TACN 要解决的核心问题

TACN 的问题空间比传统任务卸载和普通多 Agent 系统更复杂。它主要解决以下五类问题。

### 5.1 Agent 能力如何被网络发现和描述？

传统网络识别的是：

```text
设备地址、链路状态、带宽、时延、算力、存储
```

TACN 需要进一步识别：

```text
Agent 能力、模型能力、工具权限、上下文访问范围、隐私风险、当前负载、服务质量
```

也就是说，TACN 中的节点不再只是物理设备或算力节点，而是具备不同智能能力的 Agent 节点。

例如，一个摄像头不再只是视频流采集设备，而可以被抽象为：

```text
camera_agent:
  capability: visual perception, anomaly detection
  model: lightweight vision model
  tool: camera stream access
  context: local scene context
  location: terminal / edge
  privacy_level: high
  latency: low
```

这意味着 TACN 需要建立一种面向 Agent 的能力描述、注册和发现机制。

### 5.2 复杂用户意图如何转化为子任务图？

复杂任务通常不能由一个 Agent 一步完成，而需要拆解为多个具有依赖关系的子任务。

传统任务卸载系统看到的是：

```text
数据量 + 计算量 + 截止期
```

TACN 看到的是：

```text
复杂意图 + 子任务依赖 + 能力需求 + 工具需求 + 上下文需求 + 隐私约束 + 协作需求
```

例如，一个复杂意图可能被拆解为：

```text
事件检测
    |
多源信息验证
    |
上下文检索
    |
策略推理
    |
决策生成
    |
工具执行
    |
结果反馈
```

这个子任务图是 TACN 进行智能体编排的基础。

### 5.3 子任务应该分配给哪些 Agent？

每个子任务需要的能力不同，适合的 Agent 也不同。

| 子任务类型 | 所需能力 | 适合的 Agent 类型 |
| --- | --- | --- |
| 视觉确认 | vision reasoning | 摄像头 Agent / 边缘视觉 Agent |
| 传感器分析 | sensor analysis | 传感器 Agent / 边缘传感 Agent |
| 文档检索 | context retrieval | RAG Agent / 边缘知识 Agent |
| 路径规划 | planning | 边缘规划 Agent / 云端规划 Agent |
| 复杂推理 | long-context reasoning | 云端推理 Agent |
| 隐私过滤 | privacy filtering | 本地隐私 Agent |
| API 调用 | tool invocation | 工具 Agent |

因此，TACN 的关键不是"是否调用工具"，而是：

> **网络如何根据子任务需求、Agent 能力、上下文权限、工具可用性和资源状态，选择最合适的 Agent 组合。**

### 5.4 Agent 选择如何同时考虑语义、能力、资源和隐私？

普通 Agent 系统可能主要根据任务语义选择工具或子 Agent，但 TACN 必须考虑真实网络环境。

TACN 的 Agent 选择需要同时考虑：

- Agent 是否具备所需能力；
- Agent 当前是否过载；
- Agent 离数据源是否足够近；
- 任务是否需要本地隐私保护；
- 该 Agent 是否可以访问必要上下文；
- 该 Agent 是否可以调用必要工具；
- 当前网络链路是否满足时延要求；
- 是否需要终端、边缘、云端协同；
- 是否需要云端大模型兜底；
- 执行成本是否可接受。

因此，TACN 的调度依据是：

```text
语义能力匹配
+ 模型能力匹配
+ 工具可用性
+ 上下文可访问性
+ 算力资源状态
+ 网络链路状态
+ 隐私约束
+ 成本约束
+ 截止期约束
```

这也是 TACN 区别于普通 Agent Framework 的关键。

### 5.5 模型、工具、算力和上下文如何联合编排？

TACN 的核心不是单独选择一个计算节点，也不是单独选择一个模型，而是联合决定：

```text
Which Agent
+ Which Model
+ Which Tool
+ Which Context
+ Which Compute Location
+ Which Network Path
```

这就是 **Model-Tool-Compute-Context Orchestration** 的含义。

它体现了 TACN 从"算力调度"到"智能体能力编排"的升级。

---

## 6. TACN 与相关系统的区别

### 6.1 TACN 与 MEC 的区别

| 维度 | MEC | TACN |
| --- | --- | --- |
| 核心问题 | 任务是否卸载到边缘 | 复杂意图如何由多个 Agent 协同完成 |
| 输入对象 | 计算任务 | 用户复杂意图或事件触发任务 |
| 调度对象 | 计算资源、通信资源 | Agent、模型、工具、上下文、算力、网络 |
| 主要目标 | 降低时延、节省终端能耗 | 提高复杂任务完成率，并兼顾时延、隐私、成本和资源效率 |
| 智能程度 | 以资源调度为主 | 以意图理解和能力编排为核心 |

MEC 关注的是：

```text
任务放在哪里算？
```

TACN 关注的是：

```text
任务应该由哪些智能体、以什么方式协作完成？
```

### 6.2 TACN 与 CPN 的区别

CPN 强调算力可感知、可路由、可调度。

CPN 解决的问题是：

```text
哪个节点有足够算力执行任务？
```

TACN 解决的问题是：

```text
这个复杂意图需要哪些智能能力？
哪些终端、边缘和云端 Agent 能够协作完成？
如何同时满足隐私、时延、成本和资源状态约束？
```

| 维度 | CPN | TACN |
| --- | --- | --- |
| 网络对象 | 算力节点 | 智能体节点 |
| 调度对象 | CPU、GPU、带宽、存储 | Agent、模型、工具、上下文、算力和网络 |
| 任务抽象 | 计算任务 | 复杂用户意图 |
| 关键能力 | 算力感知与调度 | 意图解析、子任务拆解、能力匹配和协同编排 |
| 网络目标 | 高效计算 | 复杂意图完成 |

因此，TACN 可以看作 CPN 面向智能体时代的升级形态，但它不是 CPN 的简单扩展。它的核心变化是：

```text
从算力资源调度
    |
到智能体能力编排
```

### 6.3 TACN 与普通 Agent 系统的区别

普通 Agent 系统主要关注单个或多个软件 Agent 如何规划、推理、调用工具和完成任务。

TACN 则把 Agent 放入真实的端—边—云网络环境中，进一步考虑：

- 无线接入；
- 终端移动性；
- 边缘节点负载；
- 终端算力差异；
- 隐私边界；
- 网络链路状态；
- 多终端协作；
- 端侧数据就近处理；
- 云端大模型兜底推理。

| 维度 | 普通 Agent 系统 | TACN |
| --- | --- | --- |
| 主要对象 | 软件 Agent | 终端、边缘、云端分布式 Agent |
| 运行环境 | 云端或软件平台 | 真实端—边—云网络环境 |
| 关注重点 | 推理、规划、工具调用 | 智能体能力、网络资源、执行位置和隐私约束联合编排 |
| 资源建模 | 通常较弱 | 显式考虑算力、带宽、时延、负载和隐私 |
| 终端作用 | 多为用户入口 | 原生智能体节点 |
| 网络作用 | 通信通道 | 智能体协作与能力编排基础设施 |

所以，TACN 不是普通多 Agent 系统，而是：

> **Networked Terminal-Agent Collaboration，即网络化终端智能体协作体系。**

---

## 7. TACN 的核心主张

TACN 可以概括为一句话：

> **Future networks should not merely connect terminal devices; they should network terminal agents.**

也就是说，未来网络不应只连接终端设备，而应连接、组织和调度终端智能体。

TACN 的核心主张包括五点。

### 7.1 从设备联网到智能体联网

传统网络连接的是设备。

TACN 连接的是智能体能力。

```text
Connected Devices
    |
Networked Agents
```

终端不再只是 IP 地址背后的设备，而是具备感知、推理、工具调用和上下文访问能力的智能体节点。

### 7.2 从任务卸载到意图完成

传统 MEC 和 CPN 关注任务卸载。

TACN 关注复杂意图完成。

```text
Task Offloading
    |
Intent Fulfillment
```

网络不再只看到数据量和计算量，而是首先理解用户意图，并将意图转化为可执行的子任务图。

### 7.3 从资源调度到能力编排

传统系统调度 CPU、GPU、带宽和存储。

TACN 调度智能体能力，包括：

- 视觉理解；
- 传感器分析；
- RAG 检索；
- 工具调用；
- 路径规划；
- 安全决策；
- 多智能体协作；
- 长上下文推理。

```text
Resource Scheduling
    |
Agentic Capability Orchestration
```

### 7.4 从单点执行到多智能体协作

一个复杂任务通常无法由单个 Agent 完成，而需要终端、邻近终端、边缘节点和云端 Agent 协同执行。

```text
Single-Agent Execution
    |
Distributed Multi-Agent Collaboration
```

### 7.5 从静态网络到反馈驱动的智能闭环网络

TACN 不只是一次性调度系统，而应根据：

- 任务成功率；
- 尾部时延；
- 成本；
- 隐私风险；
- 用户反馈；
- Agent 运行状态；
- 网络资源变化；

持续优化编排策略。

---

## 8. TACN 的系统架构

TACN 可以采用"四层三面双闭环"的架构进行描述。

### 8.1 四层架构

#### L1：Agent Access and Network Weaving Layer

这一层解决：

> **分布式终端 Agent 如何接入网络，并被网络感知和管理。**

主要包括：

- 手机、摄像头、传感器、机器人、AR 眼镜、车载终端、无人机等终端接入；
- 边缘服务器和云端节点接入；
- 5G-A/6G 无线接入；
- D2D 通信；
- 端—边—云协同链路；
- 网络状态感知；
- Agent 状态暴露。

这一层的重点不是展示过多通信协议细节，而是说明：

> **TACN 首先需要把分散的终端智能体编织成一个可连接、可感知、可管理的智能体网络。**

#### L2：Agent Capability and Resource Abstraction Layer

这一层解决：

> **网络如何理解每个 Agent 能做什么，以及它当前处于什么状态。**

主要抽象内容包括：

- Agent capability profile；
- model profile；
- tool profile；
- context profile；
- compute profile；
- privacy profile；
- network state profile；
- service quality profile。

这一层是 TACN 区别于传统 CPN 的关键。

CPN 主要抽象算力资源，而 TACN 需要同时抽象：

```text
智能体能力
+ 模型能力
+ 工具能力
+ 上下文权限
+ 算力状态
+ 网络状态
+ 隐私属性
```

#### L3：Intent-Aware Agent Orchestration Layer

这一层是 TACN 的核心编排层。

它解决：

> **复杂意图如何被转化为跨 Agent、跨模型、跨工具、跨上下文和跨算力位置的执行计划。**

主要功能包括：

- 意图解析；
- 子任务图构建；
- 能力需求提取；
- Agent 发现；
- Agent 匹配；
- 模型选择；
- 工具选择；
- 上下文选择；
- 算力位置选择；
- 资源感知路由；
- 执行计划生成；
- 多智能体协同控制。

这一层必须突出，因为它是 TACN 的核心创新层。

#### L4：Agentic Service and Feedback Layer

这一层面向用户和行业应用，负责将多 Agent 协作结果转化为最终智能服务。

典型应用包括：

- 智慧园区应急响应；
- 工业设备诊断；
- 机器人协同巡检；
- 车联网协同感知；
- 智慧城市公共安全；
- 智能家居多设备协作；
- 医疗辅助服务；
- 无人机低空协同；
- 应急救援现场感知与决策。

这一层体现 TACN 的服务价值。

需要强调的是：

> **这些应用只是 TACN 的落地场景，不是 TACN 的定义边界。**

### 8.2 三个控制面

#### 1. Intent and Task Plane

该平面负责理解用户意图并生成任务结构。

主要功能包括：

- 用户请求理解；
- 意图分类；
- 子意图识别；
- 子任务图构建；
- 截止期识别；
- 隐私属性识别；
- 协作需求识别。

#### 2. Agent and Capability Plane

该平面负责维护 Agent 能力注册表，并完成能力匹配。

主要功能包括：

- Agent 注册；
- 能力描述；
- 模型能力描述；
- 工具权限描述；
- 上下文访问权限描述；
- Agent 服务质量建模；
- Agent 成本、时延和隐私风险建模；
- 子任务到 Agent 的匹配。

#### 3. Resource and Execution Plane

该平面负责资源感知和执行控制。

主要功能包括：

- 终端资源状态监测；
- 边缘资源状态监测；
- 云端资源状态监测；
- 网络链路状态监测；
- 执行位置选择；
- 任务调度；
- 多智能体协作执行；
- 执行结果反馈。

### 8.3 双闭环机制

#### 短时闭环：任务执行闭环

短时闭环关注单个复杂任务能否被成功完成。

流程为：

```text
复杂意图输入
    |
意图解析
    |
子任务拆解
    |
智能体能力匹配
    |
模型—工具—算力—上下文联合编排
    |
多智能体协作执行
    |
服务结果返回
```

该闭环关注：

- 单次任务成功率；
- 端到端时延；
- 工具调用成功率；
- 上下文命中率；
- 隐私约束是否满足；
- 任务截止期是否满足。

#### 长时闭环：系统优化闭环

长时闭环关注系统长期运行中的自适应优化。

系统根据长期运行数据持续优化：

- 意图解析策略；
- 子任务拆解策略；
- Agent 匹配策略；
- 模型选择策略；
- 工具调用策略；
- 上下文管理策略；
- 资源调度策略；
- 隐私保护策略；
- 成本控制策略。

该闭环体现 TACN 从静态编排系统向自优化智能网络演进。

---

## 9. TACN 的核心工作流程

TACN 的完整流程可以描述为：

```text
Complex User Intent
    |
Intent Abstraction
    |
Subtask Graph Construction
    |
Agent Capability Discovery
    |
Agent Capability Matching
    |
Model-Tool-Compute-Context Orchestration
    |
Distributed Agent Execution
    |
Result Aggregation and Feedback
```

### 9.1 复杂请求输入

输入可以来自用户自然语言请求，也可以来自终端事件、传感器告警、设备状态变化或系统任务触发。

TACN 面向的是通用复杂意图，而不是某一个固定场景。

### 9.2 意图解析

系统识别任务的高层意图，并提取：

- 子意图；
- 能力需求；
- 工具需求；
- 上下文需求；
- 隐私属性；
- 截止期；
- 是否需要多 Agent 协作。

### 9.3 子任务图构建

系统将复杂任务拆解为具有依赖关系的子任务图，而不是把任务当成一个整体计算负载。

子任务图可以是串行结构，也可以包含并行结构、反馈结构和条件分支。

### 9.4 智能体能力发现

系统查询 Agent Registry，了解当前网络中有哪些 Agent 可用，以及它们具备哪些能力。

### 9.5 智能体能力匹配

系统根据子任务需求选择合适 Agent。

匹配时需要综合考虑：

- 能力覆盖；
- 执行质量；
- 时延；
- 成本；
- 隐私风险；
- 当前负载；
- 工具权限；
- 上下文访问权限；
- 是否满足截止期。

### 9.6 模型—工具—算力—上下文联合编排

系统进一步决定：

- 每个子任务使用哪个模型；
- 调用哪个工具；
- 访问哪些上下文；
- 在终端、边缘还是云端执行；
- 是否需要多个 Agent 协作；
- 是否需要隐私过滤；
- 是否需要云端大模型兜底。

### 9.7 多智能体协作执行

被选中的 Agent 按照执行计划完成各自任务。

需要强调的是：

> **TACN 决定谁来做、在哪里做、用什么资源做；Agent Runtime 决定单个 Agent 内部具体怎么做。**

### 9.8 结果聚合与反馈优化

系统将多个 Agent 的执行结果聚合为最终服务结果，并记录：

- 任务是否成功；
- 总时延；
- 成本；
- 隐私风险；
- Agent 匹配是否合理；
- 工具调用是否成功；
- 上下文是否命中；
- 是否需要更新后续编排策略。

---

## 10. TACN 中不同智能体的角色

### 10.1 Terminal Agent

Terminal Agent 是部署在终端设备上的智能体。

典型设备包括：

- 手机；
- 摄像头；
- 传感器；
- 巡检机器人；
- AR 眼镜；
- 车载终端；
- 工业设备；
- 可穿戴设备；
- 无人机。

主要职责包括：

- 本地感知；
- 本地轻量推理；
- 隐私过滤；
- 用户上下文管理；
- 初步意图识别；
- 与邻近终端协作；
- 向边缘或云端发起协同请求。

Terminal Agent 的价值在于：

> **离数据源最近、时延低、隐私友好、能够利用本地上下文。**

### 10.2 Peer Agent

Peer Agent 是邻近终端上的协作智能体。

例如：

- 多个摄像头之间协作；
- 多个机器人之间协作；
- 多个传感器之间协作；
- 用户手机与 AR 眼镜协作；
- 多辆车之间协作；
- 多架无人机之间协作。

主要职责包括：

- 多终端感知融合；
- 邻近任务协作；
- 本地信息补充；
- D2D 协同；
- 降低对云端的依赖。

Peer Agent 的意义在于：

> **TACN 不只是端—边—云垂直协同，也包括终端之间的横向协同。**

### 10.3 Edge Agent

Edge Agent 部署在边缘服务器、边缘网关、路侧单元、园区边缘节点或工业边缘节点上。

主要职责包括：

- 边缘视觉理解；
- 传感器事件分析；
- 本地 RAG 检索；
- 工具调用代理；
- 多终端协作协调；
- 低时延任务执行；
- 局部隐私保护。

Edge Agent 是 TACN 的关键执行枢纽。

它既比终端具备更强算力，又比云端更接近现场，因此适合承担低时延、局部协作和隐私敏感任务。

### 10.4 Cloud Agent

Cloud Agent 部署在云端，通常具备最强模型能力、长上下文能力和全局知识整合能力。

主要职责包括：

- 复杂推理；
- 长链规划；
- 大模型推理；
- 跨区域知识整合；
- 全局策略优化；
- 复杂异常场景兜底处理。

但是，Cloud Agent 不应处理所有任务。

在 TACN 中，Cloud Agent 更适合作为：

- 高复杂度任务的兜底资源；
- 全局推理资源；
- 非强实时任务的执行资源；
- 跨区域知识整合资源。

---

## 11. TACN 的多场景适用性

TACN 是通用架构，不是为智慧园区单一场景设计的系统。

它可以应用于多类端—边—云智能服务场景。

| 应用场景 | TACN 可支撑的复杂任务 |
| --- | --- |
| 智慧园区 | 应急响应、协同安防、机器人巡检、智能会议 |
| 工业互联网 | 设备故障诊断、预测性维护、多机器人协作、生产调度 |
| 车联网 | 协同感知、道路风险判断、车路云协同决策 |
| 智慧城市 | 交通调度、公共安全、环境监测、城市应急响应 |
| 智能家居 | 多设备协同、家庭安全、老人看护、能耗管理 |
| 医疗辅助 | 可穿戴设备监测、床旁智能体协作、院内资源调度 |
| 低空经济 | 无人机协同巡检、低空交通管理、应急物资投送 |
| 应急救援 | 灾害现场感知、多机器人搜救、通信受限环境下的协作 |

这些场景虽然业务不同，但都具有共同特征：

- 终端类型多样；
- 数据分布在端、边、云不同位置；
- 任务通常具有复杂意图；
- 单个 Agent 难以独立完成；
- 需要模型、工具、上下文和算力协同；
- 存在低时延、隐私、成本和可靠性约束。

因此，TACN 的通用价值在于：

> **为多类智能服务场景提供一种复杂意图到分布式智能体协作的网络级编排机制。**

---

## 12. 智慧园区只是代表性案例

虽然 TACN 不应被定义为智慧园区系统，但智慧园区可以作为一个代表性案例。

原因是智慧园区同时包含：

- 用户手机；
- 摄像头；
- 传感器；
- 机器人；
- 门禁系统；
- 楼宇设备；
- 边缘服务器；
- 云端平台。

它天然适合展示：

- 多源感知；
- 多终端协作；
- 低时延响应；
- 隐私保护；
- 工具调用；
- 上下文检索；
- 复杂任务编排。

例如，在智慧园区中，可能出现如下任务：

```text
实验楼 A 的烟雾传感器报警，请结合摄像头画面、最近维护记录和安全规范，判断是否需要触发消防告警，并通知附近人员。
```

这个任务可以被 TACN 拆解为：

```text
传感器事件验证
    |
摄像头视觉确认
    |
维护记录检索
    |
安全规范查询
    |
风险判断
    |
告警决策
    |
通知工具调用
```

然后分配给不同智能体：

| 子任务 | 推荐智能体 |
| --- | --- |
| 传感器事件验证 | edge_sensor_agent |
| 摄像头视觉确认 | edge_vision_agent |
| 维护记录检索 | edge_rag_agent |
| 安全规则推理 | edge_safety_agent |
| 通知执行 | edge_tool_agent |

因此，智慧园区适合作为论文中的示例场景或实验场景，但不能作为 TACN 的定义边界。

正确表述应为：

> **TACN 是通用的终端智能体算力网络，智慧园区只是能够集中体现其复杂意图解析、多终端协作、低时延响应和隐私保护能力的代表性场景之一。**

---

## 13. TACN 的关键技术模块

### 13.1 Intent Parser

负责将自然语言请求或事件输入解析为结构化意图。

输出包括：

- 高层意图；
- 子意图；
- 所需能力；
- 工具需求；
- 上下文需求；
- 隐私属性；
- 截止期；
- 是否需要多 Agent 协作。

### 13.2 Subtask Graph Builder

负责将复杂意图转化为子任务图。

子任务图体现：

- 子任务顺序；
- 子任务依赖；
- 并行结构；
- 工具调用顺序；
- 上下文依赖；
- 关键路径时延。

### 13.3 Agent Registry

负责维护 Agent 能力注册表。

每个 Agent 不仅要登记位置和算力，还要登记：

- 能力集合；
- 可用模型；
- 可调用工具；
- 可访问上下文；
- 服务质量；
- 当前负载；
- 预估时延；
- 执行成本；
- 隐私风险。

### 13.4 Agent Capability Router

负责根据子任务需求和系统状态选择合适 Agent。

匹配过程不能只看资源，还要综合考虑：

- 能力覆盖；
- 模型质量；
- 工具可用性；
- 上下文可访问性；
- 隐私风险；
- 预估时延；
- 当前负载；
- 任务截止期。

### 13.5 Model-Tool-Compute-Context Orchestration

这是 TACN 的核心创新模块。

它联合决定：

- 使用哪个 Agent；
- 使用哪个模型；
- 调用哪个工具；
- 访问哪些上下文；
- 使用哪个算力位置；
- 走哪条执行路径；
- 是否需要终端、边缘、云端协同。

这一模块使 TACN 从传统算力调度升级为智能体能力编排。

### 13.6 Feedback and Optimization

负责记录执行结果，并优化后续编排策略。

反馈信息包括：

- 任务成功率；
- P95 时延；
- 成本；
- 隐私风险；
- 工具调用成功率；
- 上下文命中率；
- Agent 匹配质量；
- 云端参与比例；
- 用户反馈。

---

## 14. TACN 的评价维度

TACN 的评价不能只看平均时延。因为 TACN 面向的是复杂智能任务，所以应该同时评估任务完成质量、意图解析质量、能力匹配质量和资源使用效率。

| 指标 | 含义 |
| --- | --- |
| Task Success Rate | 复杂任务成功完成比例 |
| P95 Latency | 尾部时延，体现实时性和稳定性 |
| Intent Parsing Accuracy | 意图解析准确率 |
| Capability Matching Accuracy | 所选智能体能力是否覆盖任务需求 |
| Agent Assignment Success Rate | 是否选择到合理智能体 |
| Privacy Preservation Ratio | 隐私保护程度 |
| Cloud Offloading Ratio | 云端参与比例，体现端边能力利用 |
| Cost Efficiency | 单位成本下的任务完成效率 |
| Tool Invocation Success Rate | 工具调用成功比例 |
| Context Hit Ratio | 必要上下文是否被正确访问 |

这些指标共同说明 TACN 是否真正实现了：

```text
复杂意图理解
+ 智能体能力编排
+ 模型—工具—算力—上下文协同
+ 端—边—云多智能体协作
```

---

## 15. TACN 的创新点总结

### 创新点一：从资源中心网络转向智能体中心网络

传统网络连接设备、调度资源。

TACN 连接智能体、调度能力。

### 创新点二：从任务卸载转向复杂意图完成

TACN 不把任务仅仅看作数据量和计算量，而是看作：

```text
用户意图 + 子任务 + 工具 + 上下文 + 能力需求 + 隐私约束 + 截止期约束
```

### 创新点三：从单一算力调度转向模型—工具—算力—上下文联合编排

TACN 的调度对象不只是算力资源，而是模型、工具、上下文、智能体和执行位置的联合决策。

### 创新点四：从单 Agent 执行转向跨端—边—云多智能体协同

现有 Agent 框架主要解决单个 Agent 内部如何执行任务。

TACN 进一步解决多个分布式 Agent 如何在网络中被组织、选择、组合和协同。

### 创新点五：从被动网络转向反馈驱动的自优化智能网络

TACN 可以根据任务执行结果、资源状态、用户反馈和环境变化持续优化编排策略，使网络从静态连接基础设施演进为智能服务基础设施。

---

## 16. TACN 的准确论文主张

TACN 的论文主张不应该写成：

> We propose a new agent workflow.

因为现有 Agent 框架已经具备较成熟的 Agent 内部执行流程。

更准确的主张应该是：

> **We propose a Terminal Agent Computing Network that orchestrates distributed terminal, edge, and cloud agents for complex intent fulfillment under latency, privacy, cost, and resource constraints.**

中文表述为：

> **本文提出终端智能体算力网络 TACN，旨在将分布于终端、边缘和云端的异构智能体组织为可发现、可匹配、可调度、可协同的网络化智能资源体系，从而支撑复杂用户意图在时延、隐私、成本和资源约束下的协同完成。**

---

## 17. 给专家汇报时的核心判断句

可以用下面这段作为汇报总结：

> **TACN，Terminal Agent Computing Network，是面向 5G-A/6G 智能网络的一种通用网络化智能服务架构。现有 OpenAI Agent、Claude Agent 等框架已经具备单个 Agent 内部的推理、规划、工具调用和上下文管理能力，因此 TACN 的目标不是重新设计 Agent 内部流程，而是把分布在终端、边缘和云端的异构 Agent 组织成网络化智能资源。与传统 MEC 或 CPN 不同，TACN 的核心不是决定任务卸载到哪里，而是从复杂用户意图出发，构建子任务图，并根据任务所需能力联合编排终端、边缘和云端 Agent，同时协调模型、工具、算力、上下文和网络资源。其目标是在任务成功率、尾部时延、成本和隐私之间取得更优平衡，使未来网络从"连接设备"演进为"组织智能体完成复杂意图"的基础设施。**

---

## 18. 一句话版本

> **TACN 是一种面向终端智能体时代的通用算力网络架构，它以复杂意图为输入，以智能体能力为调度对象，以模型—工具—算力—上下文联合编排为核心机制，实现终端、边缘和云端智能体的网络化协同服务。**

---

## 19. 实现状态与路线图

### 19.1 当前实现状态

TACN 原型系统已实现四层架构的核心链路，可端到端运行。

**已实现模块：**

| 模块 | 文件 | 状态 |
|------|------|------|
| 核心数据模型 | `backend/core/models.py` | ✅ Intent、SubTask、SubTaskGraph、AgentProfile、ExecutionPlan、TaskResult |
| 意图解析器 | `backend/parser/intent_parser.py` | ✅ LLM tool-calling + JSON 解析 + 关键词兜底三级回退 |
| 子任务构建器 | `backend/parser/subtask_builder.py` | ✅ LLM 分解 + 5 种意图默认模板 |
| 能力路由器 | `backend/router/capability_router.py` | ✅ 多准则评分（能力×0.35 + 延迟×0.25 + 成本×0.15 + 隐私×0.15 + 负载×0.10） |
| MTCC 编排器 | `backend/orchestration/mtcc_orchestrator.py` | ✅ 7 维评分联合编排 |
| Agent 注册表 | `backend/registry/agent_registry.py` | ✅ 按位置/能力索引，动态注册注销 |
| LLM Agent | `backend/agent/llm_agent.py` | ✅ ReAct 循环 + dispatch map + Hook + 技能加载 + 错误降级 |
| 工具系统 | `backend/agent/tools.py` | ✅ ToolDef（函数式）+ ToolRegistry（分组管理） |
| 子 Agent 机制 | `backend/agent/subagent.py` | ✅ delegate_task 工具，fresh context + summary return |
| Agent 工厂 | `backend/agent/factory.py` | ✅ 按 location 创建，自动注入 delegate_task |
| 并行执行 | `backend/agent/factory.py` | ✅ asyncio.gather 按 parallel_groups 并行 |
| 上下文传递 | `backend/orchestration/tacn_system.py` | ✅ 上游 agent 结果自动注入下游 |
| 上下文压缩 | `backend/agent/llm_agent.py` | ✅ microcompact 清理旧 tool_result |
| LLM 重试 | `backend/agent/llm_agent.py` | ✅ 指数退避 3 次重试 |
| 错误降级 | `backend/agent/llm_agent.py` | ✅ 正常→简化prompt→减少工具→兜底 |
| Hook 系统 | `backend/agent/llm_agent.py` | ✅ PreToolUse / PostToolUse |
| 技能加载 | `backend/agent/llm_agent.py` | ✅ SkillLoader 运行时注入领域知识 |
| 消息持久化 | `backend/agent/message.py` | ✅ JSONL 文件邮箱模式 |
| 隐私过滤 | `backend/agent/terminal_agent.py` | ✅ 敏感字段脱敏 |
| 执行反馈 | `backend/orchestration/feedback.py` | ⚠️ 资源环已实现，服务环为空 |
| LLM 客户端 | `backend/llm/client.py` | ✅ OpenAI 兼容 + Mock 回退 |

**验证结果：**

- 端到端流水线可运行：用户请求 → 意图解析 → 子任务分解 → MTCC 路由 → Agent ReAct 执行 → 结果汇总
- 真实 LLM (mimo-v2.5) 驱动，tool-calling 正常工作
- 并行执行、上下文传递、Hook 系统均已验证通过

### 19.2 待完成工作

#### P0 — 落地必需

- [ ] **数据池 + HTTP API**：当前工具返回硬编码 mock 数据，需实现轻量数据池，外部通过 HTTP POST 灌入真实数据，工具从池中读取最新值
- [ ] **工具适配层**：定义 `sensor_data`、`image_data`、`alert_data` 等标准数据结构，工具 handler 从数据池读取而非返回 mock
- [ ] **反馈闭环补全**：`ExecutionFeedback.update_service_policy` 当前为空，需实现意图-服务优化环

#### P1 — 体验优化

- [ ] **Web API 服务**：FastAPI/Flask 暴露 `POST /api/execute` 接口，前端可发送自然语言请求并获取执行结果
- [ ] **执行过程可视化**：实时展示意图解析、子任务 DAG、Agent 分配、工具调用过程
- [ ] **deadline 自适应**：当前 deadline 是硬编码默认值，应根据 LLM 实际延迟动态调整

#### P2 — 能力增强

- [ ] **真实工具适配器**：MQTT 传感器、RTSP 摄像头、HTTP 告警 API 适配器（等场景确定后实现）
- [ ] **后台任务**：长时间操作（网络搜索、大文件分析）异步执行，不阻塞 ReAct 循环
- [ ] **Agent 间实时协作**：执行中的 agent 可主动向其他 agent 发消息求助（当前只有上游上下文注入）
- [ ] **会话记忆**：跨任务的 agent 记忆系统，参考 LCC 的 Memory 模块
- [ ] **意图解析模板扩展**：当前仅支持 5 种意图类型，需扩展为通用意图解析

### 19.3 架构参考

Agent 实现参考了 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 的 Harness 工程模式：

- 核心 ReAct 循环与 LCC agent_loop 同构
- 工具系统采用 dispatch map 模式（ToolDef 函数式注册）
- 子 Agent 采用 fresh context + summary return 模式
- 上下文管理采用 microcompact 模式
- 错误处理采用重试 + 降级策略

TACN 与 LCC 的核心区别：LCC 是全自主 Agent（用户给目标，Agent 自己决定做什么），TACN 是编排驱动的执行 Agent（编排层决定做什么，Agent 决定怎么做）。这是面向 IoT 场景的设计选择，不是缺陷。
