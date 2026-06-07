"""子 Agent 机制 — 参考 LCC 的 task 工具模式.

LCC 的核心洞察:
  "Subagent = fresh context. 子 agent 有自己的 messages，
   干完活只把摘要带回父 agent，上下文隔离。"

TACN 中的用途:
  agent 可以通过 delegate_task 工具，把一部分工作委托给另一个 agent。
  被委托的 agent 有全新的上下文，只返回结果摘要。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from backend.agent.llm_agent import LLMAgent
from backend.agent.tools import ToolDef, ToolRegistry
from backend.core.models import SubTask, CapabilityRequirement, CapabilityType

logger = logging.getLogger(__name__)


class SubAgentManager:
    """子 Agent 管理器 — 提供 delegate_task 工具.

    用法:
        subagent_mgr = SubAgentManager(agents, llm_client)
        # 注册 delegate_task 工具到 agent 的工具集
        tool = subagent_mgr.create_delegate_tool("edge_agent_001")
    """

    def __init__(self, agents: dict[str, LLMAgent]):
        self._agents = agents

    def create_delegate_tool(self, caller_agent_id: str) -> ToolDef:
        """为指定 agent 创建 delegate_task 工具.

        agent 调用此工具时，会 spawn 一个子 agent 执行任务，
        子 agent 有全新上下文，只返回摘要。
        """
        async def delegate_task(task_description: str, target_agent_id: str = "") -> dict:
            """委托任务给另一个 agent (子 agent 模式).

            子 agent 有全新的上下文，共享工具但不共享对话历史。
            只返回执行结果摘要。
            """
            # 如果没指定 target，自动选一个
            if not target_agent_id:
                target = self._pick_best_agent(task_description, caller_agent_id)
            else:
                target = self._agents.get(target_agent_id)

            if target is None:
                return {"success": False, "error": f"未找到可用的 agent: {target_agent_id}"}

            # 创建子任务
            subtask = SubTask(
                name="delegated_subtask",
                description=task_description,
            )

            # 子 agent 执行 — 全新上下文 (LCC 模式)
            result = await target.execute(subtask, context=None)

            # 只返回摘要 (LCC 模式: 子 agent 上下文丢弃)
            return {
                "success": result.success,
                "agent": target.name,
                "agent_type": type(target).__name__,
                "output": str(result.output)[:3000] if result.output else None,
                "error": result.error,
                "latency_ms": result.latency_ms,
            }

        return ToolDef(
            name="delegate_task",
            description="委托任务给其他 agent 执行。子 agent 有独立上下文，只返回结果摘要。适用于需要其他层级能力辅助的场景。",
            parameters={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "要委托的任务描述",
                    },
                    "target_agent_id": {
                        "type": "string",
                        "description": "目标 agent ID (留空则自动选择)",
                    },
                },
                "required": ["task_description"],
            },
            handler=delegate_task,
        )

    def _pick_best_agent(self, task_description: str, exclude_id: str) -> Optional[LLMAgent]:
        """根据任务描述自动选择最佳 agent (简单策略)."""
        # 优先选 edge (能力/成本平衡)，其次 cloud
        candidates = [
            a for aid, a in self._agents.items()
            if aid != exclude_id
        ]
        if not candidates:
            return None

        # 按优先级: edge > cloud > peer > terminal
        priority = {"edge": 0, "cloud": 1, "peer": 2, "terminal": 3}
        candidates.sort(key=lambda a: priority.get(a.location.value, 99))
        return candidates[0]
