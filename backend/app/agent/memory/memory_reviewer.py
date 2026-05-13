"""MemoryReviewer — LLM-driven post-session memory review.

After a session ends, analyses the conversation transcript to extract
user preferences, habits, and environment information that should be
persisted into MEMORY.md or USER.md, without relying on the agent to
proactively call the memory tool.
"""

import json
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.agent.memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)

LLMCallFn = Callable[[str], Coroutine[Any, Any, str]]

MEMORY_REVIEW_PROMPT = """分析以下对话记录，提取需要长期记住的信息。

## 提取规则
1. 用户偏好：创作风格、关注领域、语言习惯 → 存入 user
2. 工作习惯：常用工具组合、分析框架、操作流程 → 存入 memory
3. 环境信息：用户身份、账号关联、技术环境 → 存入 user
4. 不要存：一次性问题、临时话题、已有记忆中的重复内容

## 现有记忆
{existing_memory}

## 现有用户画像
{existing_user}

## 对话记录
{transcript}

输出 JSON:
{{"updates": [
  {{"target": "user|memory", "action": "add|replace|remove",
    "content": "内容", "old_text": "仅replace/remove需要"}}
]}}
如无需更新返回 {{"updates": []}}"""


def _format_messages_for_review(messages: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    parts: List[str] = []
    total = 0
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in content
            )
        if not content:
            continue
        line = f"[{role}]: {content[:800]}"
        if total + len(line) > max_chars:
            break
        parts.append(line)
        total += len(line)
    return "\n\n".join(parts)


class MemoryReviewer:
    """Analyses conversation transcripts and auto-updates memory stores."""

    def __init__(self, llm_call: LLMCallFn):
        self._llm_call = llm_call

    async def review_session(
        self,
        messages: List[Dict[str, Any]],
        memory_store: MemoryStore,
    ) -> int:
        """Review a session transcript and apply memory updates.

        Returns the number of successful updates applied.
        """
        transcript = _format_messages_for_review(messages)
        if not transcript.strip():
            return 0

        existing_memory = "\n".join(memory_store.memory_entries) if memory_store.memory_entries else "(空)"
        existing_user = "\n".join(memory_store.user_entries) if memory_store.user_entries else "(空)"

        prompt = MEMORY_REVIEW_PROMPT.format(
            existing_memory=existing_memory,
            existing_user=existing_user,
            transcript=transcript,
        )

        try:
            raw = await self._llm_call(prompt)
        except Exception as e:
            logger.error("Memory review LLM call failed: %s", e)
            return 0

        updates = self._parse_updates(raw)
        if not updates:
            return 0

        applied = 0
        for upd in updates:
            target = upd.get("target", "")
            action = upd.get("action", "")
            content = upd.get("content", "")
            old_text = upd.get("old_text", "")

            if target not in ("memory", "user"):
                continue

            try:
                if action == "add" and content:
                    result = memory_store.add(target, content)
                elif action == "replace" and old_text and content:
                    result = memory_store.replace(target, old_text, content)
                elif action == "remove" and old_text:
                    result = memory_store.remove(target, old_text)
                else:
                    continue

                if result.get("success"):
                    applied += 1
                    logger.debug("Memory review: %s %s -> %s", action, target, content[:60])
                else:
                    logger.debug("Memory review skipped: %s", result.get("error", ""))
            except Exception as e:
                logger.warning("Memory review update error: %s", e)

        return applied

    @staticmethod
    def _parse_updates(raw: str) -> List[Dict[str, Any]]:
        """Extract the updates array from LLM response JSON."""
        raw = raw.strip()
        # Try to find JSON in the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return []
        try:
            data = json.loads(raw[start:end])
            updates = data.get("updates", [])
            if isinstance(updates, list):
                return updates
        except (json.JSONDecodeError, AttributeError):
            pass
        return []
