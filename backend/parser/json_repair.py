"""JSON 修复管道.

参考 deer-flow 的 repair_json_output，处理 LLM 输出的常见格式问题:
- markdown 代码块包裹
- 首尾多余字符
- 尾逗号
- 单引号替代双引号
"""

from __future__ import annotations

import re


def repair_json_output(text: str) -> str:
    """修复 LLM 输出的 JSON 格式问题.

    Args:
        text: LLM 原始输出

    Returns:
        修复后的 JSON 字符串
    """
    if not text or not text.strip():
        return text

    cleaned = text.strip()

    # 1. 去除 markdown 代码块包裹
    # ```json\n...\n``` 或 ```\n...\n```
    code_block_pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(code_block_pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()

    # 2. 找到第一个 { 或 [ 和最后一个 } 或 ]
    # 用于去除前后的非 JSON 文本（如 "以下是结果："）
    first_brace = -1
    first_bracket = -1
    for i, ch in enumerate(cleaned):
        if ch == "{":
            first_brace = i
            break
        if ch == "[":
            first_bracket = i
            break

    if first_brace >= 0 or first_bracket >= 0:
        start = first_brace if first_brace >= 0 else first_bracket
        # 找最后一个匹配的闭合符号
        end = -1
        close_char = "}" if first_brace >= 0 else "]"
        for i in range(len(cleaned) - 1, start - 1, -1):
            if cleaned[i] == close_char:
                end = i
                break
        if end > start:
            cleaned = cleaned[start : end + 1]

    # 3. 修复尾逗号: ,} -> } 和 ,] -> ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    # 4. 修复单引号字符串 -> 双引号
    # 仅处理键和简单字符串值，避免破坏嵌套结构
    cleaned = _fix_single_quotes(cleaned)

    return cleaned


def _fix_single_quotes(text: str) -> str:
    """将单引号字符串替换为双引号.

    简单实现：匹配 'key': 'value' 模式。
    对于复杂嵌套 JSON 可能不够精确，但足以处理 LLM 常见输出。
    """
    # 替换键: 'key' -> "key"
    text = re.sub(r"(?<=[{,\n])\s*'([^']+)'\s*:", r' "\1":', text)
    # 替换字符串值: 'value' -> "value"（不替换数字/布尔/null）
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
    return text
