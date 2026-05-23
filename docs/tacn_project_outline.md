# TACN 项目概念基准

> 本文档定义 TACN 的核心概念、理论基础和架构规范。
> 代码实现应以此文档为基准，确保变化仍服务于 TACN 主链路。

---

## TACN 核心链路

```text
complex intent
-> intent parsing
-> subtask graph
-> agent capability matching
-> model-tool-compute-context orchestration (MTCC)
-> collaborative execution
-> feedback optimization
```

## TACN 形式化定义

```math
\mathcal{N}^{\mathrm{TACN}}
=
\left(
\mathcal{A}, \mathcal{M}, \mathcal{U}, \mathcal{C}, \mathcal{R}, \mathcal{I}
\right)
```

- $\mathcal{A}$: 智能体集合
- $\mathcal{M}$: 模型集合
- $\mathcal{U}$: 工具集合
- $\mathcal{C}$: 上下文集合
- $\mathcal{R}$: 资源状态集合
- $\mathcal{I}$: 用户意图/任务集合

## 四层架构

| 层级 | 名称 | 核心职责 |
|---|---|---|
| L1 | 端-网-边-云基础设施层 | 通信、计算、感知、存储、执行环境 |
| L2 | 智能体资源与能力抽象层 | Agent/Model/Tool/Context Registry |
| L3 | 意图感知的智能体编排与协作层 | 意图解析、子任务图、MTCC 编排 |
| L4 | 智能服务与应用层 | 意图入口、业务接口、场景适配 |

## 三控制面

1. **资源控制面**: 资源监测、负载感知、队列估计、拥塞控制
2. **语义与智能体控制面**: 意图解析、能力发现、协作管理
3. **信任安全隐私控制面**: 隐私识别、数据脱敏、权限控制、可信评估

## 双闭环优化

- **资源-能力优化环**: 资源感知 → 能力建模 → MTCC 编排 → 执行反馈 → 状态更新
- **意图-服务优化环**: 意图 → 解析 → 任务图 → 匹配 → 执行 → 反馈 → 策略更新

## 通用任务族

| 任务族 | 关注能力 |
|---|---|
| `event_response` | 低时延、隐私、安全推理、工具调用、多智能体协作 |
| `mobile_inspection` | 传感器分析、设备查询、维护记录、路径规划 |
| `collaborative_perception` | 多终端感知、多模态融合、风险判断 |
| `context_aware_decision` | RAG 检索、设备日志、规则推理、决策支持 |
| `personal_assistant_service` | 日程、通知、用户上下文、隐私过滤、工具调用 |
