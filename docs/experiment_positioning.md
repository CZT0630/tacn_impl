# TACN-Proto 实验定位

> 本文档定义 TACN-Proto 原型的实验范围、对比方法和评价指标。

---

## 实验目标

TACN-Proto 是用于验证 TACN 核心思想的轻量级实验原型，验证以下问题：

1. 复杂用户意图是否可以被解析为结构化任务表示
2. 复杂任务是否可以被转换为子任务图
3. 子任务是否可以根据能力需求匹配到合适智能体
4. 模型、工具、算力和上下文是否可以被联合编排 (MTCC)
5. 多智能体协作执行是否可以被记录、评估和反馈
6. TACN 是否能在任务成功率、尾部时延、隐私保护和成本之间取得更优折中

## 对比方法

| 方法 | 描述 |
|---|---|
| Cloud-Only | 所有任务发送到云端执行 |
| Resource-Aware CPN | 基于资源状态的传统算力网络调度 |
| LLM Semantic Router | 仅使用 LLM 进行语义路由，无 MTCC |
| TACN-O (本方法) | 完整 TACN 编排：意图解析 + 子任务图 + 能力匹配 + MTCC |

## 消融实验

| 消融项 | 去掉什么 |
|---|---|
| w/o LLM Intent | 用关键词规则替代 LLM 意图解析 |
| w/o Capability Matching | 随机分配 Agent，不做能力匹配 |
| w/o Resource Awareness | 不考虑资源状态和负载 |
| w/o Tool-Context Awareness | 不考虑工具和上下文可用性 |
| w/o Terminal Agents | 移除终端智能体，只有边缘和云 |

## 核心评价指标

| 指标 | 含义 |
|---|---|
| Task Success Rate | 复杂任务成功完成比例 |
| P95 Latency | 尾部任务时延 |
| Intent Parsing Accuracy | 意图解析准确率 |
| Capability Matching Accuracy | 智能体能力匹配准确率 |
| Privacy Preservation Ratio | 隐私保护比例 |
| Cloud Offloading Ratio | 云端参与比例 |
| Cost Efficiency | 成本效率 (成功任务数/总成本) |
| Tool Success Rate | 工具调用成功率 |
| Context Hit Rate | 上下文命中率 |

## 表述边界

推荐表述：

> 本项目构建了一个轻量级 TACN 原型，用于验证复杂意图解析、子任务图生成、
> 智能体能力匹配和模型-工具-算力-上下文联合编排的可行性。

不推荐表述：

> This system fully implements a real-world terminal agent computing network.
