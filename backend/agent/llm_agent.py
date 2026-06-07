"""LLM Agent — 基于大语言模型的智能体，ReAct 工具调用循环.

参考 learn-claude-code 的 harness 模式:
- 工具是 dispatch map (name → handler)，不是类继承
- 子 agent = 全新 messages 上下文，只返回摘要
- 上下文压缩: tool result 过长时自动截断
- 最大迭代后返回 LLM 当前的思考，而非丢弃
- Hook 系统: 工具调用前后可插入审计/限流/权限逻辑
- 技能加载: 运行时按需注入领域知识
- 错误降级: 重试失败后尝试备选策略
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional

from backend.agent.base import BaseAgent
from backend.agent.tools import AgentTool, ToolDef, ToolRegistry, tools_to_openai_schema, tools_by_name
from backend.core.models import (
    AgentProfile,
    SubTask,
    SubTaskResult,
)

if TYPE_CHECKING:
    from backend.agent.message import MessageBus
    from backend.llm.client import LLMClient

logger = logging.getLogger(__name__)

# ============================================================================
# 配置常量
# ============================================================================

TOOL_RESULT_MAX_CHARS = 8000
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0


# ============================================================================
# Hook 系统 — 参考 LCC 的 PreToolUse / PostToolUse
# ============================================================================

@dataclass
class ToolCallEvent:
    """工具调用事件 — 传递给 Hook 的上下文."""
    agent_name: str
    tool_name: str
    arguments: dict[str, Any]
    result: str = ""
    error: str = ""
    duration_ms: float = 0.0
    iteration: int = 0
    blocked: bool = False       # PreToolUse 可设置为 True 阻止调用
    replacement: str = ""       # PreToolUse 可替换结果


# Hook 类型: async (event) -> None
HookFn = Callable[[ToolCallEvent], Coroutine[Any, Any, None]]


class HookRegistry:
    """Hook 注册表 — 管理 PreToolUse / PostToolUse 回调.

    用法:
        hooks = HookRegistry()
        hooks.on_pre_tool_use(my_audit_hook)
        hooks.on_post_tool_use(my_logging_hook)
    """

    def __init__(self):
        self._pre_hooks: list[HookFn] = []
        self._post_hooks: list[HookFn] = []

    def on_pre_tool_use(self, hook: HookFn):
        """注册工具调用前的 Hook."""
        self._pre_hooks.append(hook)

    def on_post_tool_use(self, hook: HookFn):
        """注册工具调用后的 Hook."""
        self._post_hooks.append(hook)

    async def fire_pre(self, event: ToolCallEvent) -> ToolCallEvent:
        """触发所有 PreToolUse Hook. 返回 event (可能被修改)."""
        for hook in self._pre_hooks:
            try:
                await hook(event)
            except Exception as e:
                logger.warning(f"PreToolUse hook error: {e}")
        return event

    async def fire_post(self, event: ToolCallEvent):
        """触发所有 PostToolUse Hook."""
        for hook in self._post_hooks:
            try:
                await hook(event)
            except Exception as e:
                logger.warning(f"PostToolUse hook error: {e}")


# ============================================================================
# 技能加载 — 参考 LCC 的 SkillLoader
# ============================================================================

class SkillLoader:
    """技能加载器 — 运行时按需注入领域知识.

    用法:
        loader = SkillLoader("skills/")
        loader.load_from_dir()              # 扫描目录加载所有 SKILL.md
        knowledge = loader.get_skill("fire_emergency")
    """

    def __init__(self, skills_dir: str = ""):
        self._skills_dir = skills_dir
        self._skills: dict[str, dict] = {}

    def load_from_dir(self, skills_dir: str = ""):
        """从目录加载 SKILL.md 文件."""
        from pathlib import Path
        d = Path(skills_dir or self._skills_dir)
        if not d.exists():
            return
        for f in sorted(d.rglob("SKILL.md")):
            text = f.read_text(encoding="utf-8")
            name = f.parent.name
            self._skills[name] = {"name": name, "body": text}

    def register(self, name: str, body: str):
        """手动注册技能."""
        self._skills[name] = {"name": name, "body": body}

    def get_skill(self, name: str) -> str | None:
        """获取技能内容."""
        skill = self._skills.get(name)
        return skill["body"] if skill else None

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())

    def inject_into_prompt(self, system_prompt: str, skill_names: list[str]) -> str:
        """将指定技能注入 system prompt."""
        parts = [system_prompt]
        for name in skill_names:
            body = self.get_skill(name)
            if body:
                parts.append(f"\n\n<skill name=\"{name}\">\n{body}\n</skill>")
        return "\n".join(parts)


# ============================================================================
# 错误降级 — 参考 LCC 的 error recovery
# ============================================================================

@dataclass
class FallbackStrategy:
    """错误降级策略."""
    # 重试次数用尽后，尝试的备选方案
    use_simpler_prompt: bool = True      # 简化 prompt 重试
    reduce_tools: bool = True            # 减少工具数量重试
    fallback_text: str = ""              # 直接返回的兜底文本


# ============================================================================
# 工具函数
# ============================================================================

async def _call_llm_with_retry(llm_client, messages, tools=None, max_retries=LLM_MAX_RETRIES):
    """调用 LLM — 带指数退避重试."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await llm_client.chat(messages=messages, tools=tools)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries}): {e}, retry in {delay:.1f}s")
                await asyncio.sleep(delay)
    raise last_error


def _truncate(text: str, max_chars: int = TOOL_RESULT_MAX_CHARS) -> str:
    """截断过长的 tool result."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"


def _microcompact(messages: list[dict], keep_recent: int = 3):
    """上下文压缩 — 只保留最近 N 个 tool_result，旧的标记为 [cleared]."""
    tool_result_indices = [
        i for i, m in enumerate(messages)
        if m.get("role") == "tool" and len(m.get("content", "")) > 200
    ]
    if len(tool_result_indices) <= keep_recent:
        return
    for idx in tool_result_indices[:-keep_recent]:
        messages[idx]["content"] = "[cleared - see earlier in conversation]"


# ============================================================================
# LLM Agent
# ============================================================================

class LLMAgent(BaseAgent):
    """基于 LLM 的智能体 — ReAct 循环.

    核心循环 (与 LCC agent_loop 同构):
        while True:
            response = LLM(messages, tools)
            if not tool_calls: return content
            for tc in tool_calls:
                pre_hook(event)         # 可阻止/替换
                result = dispatch(tc)
                post_hook(event)        # 可审计/记录
                messages.append(result)

    增强:
    - Hook 系统: PreToolUse / PostToolUse
    - 技能加载: 运行时注入领域知识
    - 错误降级: 重试 → 简化 prompt → 减少工具 → 兜底文本
    - 上下文压缩: microcompact
    - 上游上下文注入
    """

    MAX_ITERATIONS = 8

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClient | None = None,
        message_bus: Optional[MessageBus] = None,
        tools: list[ToolDef | AgentTool] | None = None,
        system_prompt: str = "",
        tool_registry: Optional[ToolRegistry] = None,
        hooks: Optional[HookRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        super().__init__(profile, message_bus)
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.hooks = hooks or HookRegistry()
        self.skill_loader = skill_loader

        # 构建工具集合
        if tools:
            self._tools = tools
        elif tool_registry and profile.location:
            self._tools = tool_registry.get_tools_for(profile.location.value)
        else:
            self._tools = []

        # dispatch map
        self._dispatch: dict[str, ToolDef | AgentTool] = {t.name: t for t in self._tools}
        # OpenAI schema
        self._openai_tools = [t.to_openai_tool() for t in self._tools] if self._tools else None
        # system prompt
        self._base_system_prompt = system_prompt or self._default_system_prompt()
        self.system_prompt = self._build_system_prompt()

    def _default_system_prompt(self) -> str:
        caps = [c.capability_type.value for c in self.profile.capabilities]
        tool_names = list(self._dispatch.keys())
        return (
            f"你是 {self.name}，部署在 {self.location.value} 层的 AI 智能体。\n"
            f"你的能力: {', '.join(caps)}\n"
            f"可用工具: {', '.join(tool_names)}\n"
            f"请根据任务描述，使用可用工具完成任务。"
            f"如果不需要工具即可回答，直接给出结果。"
        )

    def _build_system_prompt(self) -> str:
        """构建 system prompt — 可注入技能知识."""
        prompt = self._base_system_prompt
        if self.skill_loader:
            skills = self.skill_loader.list_skills()
            if skills:
                prompt = self.skill_loader.inject_into_prompt(prompt, skills)
        return prompt

    # ------------------------------------------------------------------
    # 核心执行
    # ------------------------------------------------------------------

    async def execute(self, subtask: SubTask, context: dict | None = None) -> SubTaskResult:
        """执行子任务 — ReAct 循环 + 错误降级."""
        start = time.time()

        try:
            if self.llm_client and self._openai_tools:
                result_text = await self._react_loop_with_fallback(subtask, context)
            else:
                result_text = await self._simple_execute(subtask, context)

            latency_ms = (time.time() - start) * 1000
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=self.id,
                location=self.location,
                success=True,
                output=result_text,
                latency_ms=latency_ms,
                cost=self.profile.cost_per_invocation,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(f"Agent {self.name} execute failed: {e}")
            return SubTaskResult(
                subtask_id=subtask.id,
                agent_id=self.id,
                location=self.location,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    async def _react_loop_with_fallback(self, subtask: SubTask, context: dict | None) -> str:
        """ReAct 循环 + 错误降级.

        策略:
        1. 正常执行 (完整 prompt + 全部工具)
        2. 重试失败 → 简化 prompt 重试
        3. 仍失败 → 减少工具数量重试
        4. 全部失败 → 返回兜底文本
        """
        try:
            return await self._react_loop(subtask, context)
        except Exception as e:
            logger.warning(f"Agent {self.name} normal loop failed: {e}, trying fallback")

        # 降级 1: 简化 prompt
        try:
            simple_prompt = f"你是 {self.name}。请完成以下任务:\n{subtask.name}: {subtask.description}"
            return await self._react_loop(subtask, context, override_prompt=simple_prompt)
        except Exception as e:
            logger.warning(f"Agent {self.name} simplified prompt failed: {e}")

        # 降级 2: 减少工具 (只保留前 2 个)
        try:
            reduced_tools = self._openai_tools[:2] if self._openai_tools else None
            return await self._react_loop(subtask, context, override_tools=reduced_tools)
        except Exception:
            pass

        # 降级 3: 兜底
        return f"[Agent {self.name}] 任务 '{subtask.name}' 执行失败，已尝试所有降级策略。错误: {e}"

    async def _react_loop(
        self,
        subtask: SubTask,
        context: dict | None,
        override_prompt: str | None = None,
        override_tools: list[dict] | None = None,
    ) -> str:
        """ReAct 循环 — 核心执行逻辑."""
        messages = self._build_messages(subtask, context, override_prompt)
        tools = override_tools or self._openai_tools
        last_response = None

        for iteration in range(self.MAX_ITERATIONS):
            # 上下文压缩
            _microcompact(messages, keep_recent=3)

            response = await _call_llm_with_retry(
                self.llm_client, messages, tools=tools
            )
            last_response = response

            # LLM 给出最终答案
            if response.content and not response.tool_calls:
                return response.content

            # LLM 决定调用工具
            if response.tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # 执行工具 — 带 Hook
                for tc in response.tool_calls:
                    event = ToolCallEvent(
                        agent_name=self.name,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        iteration=iteration,
                    )

                    # PreToolUse Hook — 可阻止调用
                    event = await self.hooks.fire_pre(event)
                    if event.blocked:
                        result_str = event.replacement or f"工具 {tc.name} 被阻止"
                    elif event.replacement:
                        result_str = event.replacement
                    else:
                        # 正常执行
                        tool = self._dispatch.get(tc.name)
                        if tool:
                            tool_start = time.time()
                            try:
                                raw_result = await tool.execute(**tc.arguments)
                                result_str = _truncate(json.dumps(raw_result, ensure_ascii=False, default=str))
                                event.result = result_str
                                event.duration_ms = (time.time() - tool_start) * 1000
                            except Exception as e:
                                result_str = f"工具执行失败: {e}"
                                event.error = str(e)
                        else:
                            result_str = f"未知工具: {tc.name}"

                    # PostToolUse Hook — 审计/记录
                    await self.hooks.fire_post(event)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })
            else:
                return "[Agent] LLM 未返回有效响应"

        # 超过最大迭代
        if last_response and last_response.content:
            return last_response.content
        return f"[Agent] 达到最大迭代次数 ({self.MAX_ITERATIONS})"

    async def _simple_execute(self, subtask: SubTask, context: dict | None) -> str:
        """简单执行 (无 LLM 或无工具时的回退)."""
        if self.llm_client:
            messages = self._build_messages(subtask, context)
            response = await self.llm_client.chat(messages=messages)
            return response.content or "[Agent] LLM 未返回内容"
        return f"[Mock] {self.name} 已完成子任务: {subtask.name}"

    # ------------------------------------------------------------------
    # 消息构建
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        subtask: SubTask,
        context: dict | None,
        override_prompt: str | None = None,
    ) -> list[dict]:
        """构建 LLM 对话消息."""
        messages = [{"role": "system", "content": override_prompt or self.system_prompt}]

        # 任务描述
        task_desc = f"## 任务\n名称: {subtask.name}\n描述: {subtask.description}"
        if subtask.required_capabilities:
            caps = [c.capability_type.value for c in subtask.required_capabilities]
            task_desc += f"\n需要的能力: {', '.join(caps)}"

        # 注入上游结果
        if context:
            upstream = context.get("upstream_results", {})
            if upstream:
                task_desc += "\n\n## 上游任务结果 (供参考)"
                for st_id, result in upstream.items():
                    agent_name = result.get("agent_name", st_id)
                    output = result.get("output", "")
                    if output:
                        output_str = str(output)
                        if len(output_str) > 2000:
                            output_str = output_str[:2000] + "..."
                        task_desc += f"\n\n### {agent_name}\n{output_str}"

            other_ctx = {k: v for k, v in context.items() if k != "upstream_results"}
            if other_ctx:
                task_desc += f"\n\n## 其他上下文\n{json.dumps(other_ctx, ensure_ascii=False, default=str)[:3000]}"

        messages.append({"role": "user", "content": task_desc})
        return messages
