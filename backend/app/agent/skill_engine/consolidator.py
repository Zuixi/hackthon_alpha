"""SkillConsolidator — merge multiple similar skills into one via LLM.

When the similarity engine detects N similar skills, this module produces
a single consolidated SKILL.md by having the LLM re-synthesize triggers,
workflows, and descriptions from all inputs.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)

LLMCallFn = Callable[[str], Coroutine[Any, Any, str]]

_MERGE_PROMPT = """你是一个 Skill 合并专家。以下是 {count} 个被判定为高度相似的 Skill，请将它们合并为 1 个更完整的 Skill。

## 合并规则
1. **triggers**: 取所有 skill 的 triggers 并集，去重
2. **tools**: 取所有 skill 的 tools 并集，去重
3. **description**: 写一个更概括的描述，覆盖所有原 skill 的范围
4. **name**: 使用 kebab-case，取一个能覆盖所有原 skill 含义的名称
5. **body**: 合并所有工作流程步骤，保留每个 skill 的独特流程，消除重复，优化整体结构

## 原始 Skills

{skills_content}

## 输出格式

严格输出以下 JSON（不要输出其他内容）：
{{
  "name": "merged-skill-name",
  "description": "合并后的描述",
  "triggers": ["触发词1", "触发词2", ...],
  "tools": ["tool1", "tool2", ...],
  "body": "## 工作流程\\n\\n（合并后的完整 Markdown 内容）"
}}"""


@dataclass
class MergeResult:
    success: bool
    merged_skill: Optional[Dict[str, Any]] = None
    old_names: List[str] = None
    error: str = ""

    def __post_init__(self):
        if self.old_names is None:
            self.old_names = []


class SkillConsolidator:
    """Merge multiple similar skills into one using LLM."""

    def __init__(self, llm_call: Optional[LLMCallFn] = None):
        self._llm_call = llm_call

    def set_llm_call(self, fn: LLMCallFn) -> None:
        self._llm_call = fn

    async def merge(self, skills: List[Dict[str, Any]]) -> MergeResult:
        """Merge N skills into 1 using LLM.

        Args:
            skills: list of skill dicts with keys: name, description, triggers, tools, body

        Returns:
            MergeResult with the consolidated skill.
        """
        if not skills:
            return MergeResult(success=False, error="No skills to merge")

        if len(skills) == 1:
            return MergeResult(success=True, merged_skill=skills[0], old_names=[skills[0].get("name", "")])

        if not self._llm_call:
            return MergeResult(success=False, error="LLM call function not configured")

        old_names = [s.get("name", "") for s in skills]

        # Build prompt content
        parts = []
        for i, skill in enumerate(skills, 1):
            part = f"### Skill {i}: {skill.get('name', '?')}\n"
            part += f"描述: {skill.get('description', '')}\n"
            part += f"触发词: {', '.join(skill.get('triggers', []))}\n"
            part += f"工具: {', '.join(skill.get('tools', []))}\n"
            body = skill.get("body", "")
            if len(body) > 3000:
                body = body[:3000] + "\n...[truncated]"
            part += f"内容:\n{body}\n"
            parts.append(part)

        prompt = _MERGE_PROMPT.format(
            count=len(skills),
            skills_content="\n---\n".join(parts),
        )

        try:
            response = await self._llm_call(prompt)
            text = response.strip()

            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                return MergeResult(success=False, old_names=old_names, error="LLM did not return valid JSON")

            data = json.loads(json_match.group())

            # Validate required fields
            required = {"name", "description", "triggers", "tools", "body"}
            missing = required - set(data.keys())
            if missing:
                return MergeResult(
                    success=False, old_names=old_names,
                    error=f"Merged skill missing fields: {missing}",
                )

            # Ensure types
            merged = {
                "name": str(data["name"]),
                "description": str(data["description"])[:1024],
                "triggers": [str(t) for t in data["triggers"]] if isinstance(data["triggers"], list) else [],
                "tools": [str(t) for t in data["tools"]] if isinstance(data["tools"], list) else [],
                "body": str(data["body"]),
            }

            logger.info(
                "Merged %d skills [%s] -> '%s'",
                len(skills), ", ".join(old_names), merged["name"],
            )

            return MergeResult(success=True, merged_skill=merged, old_names=old_names)

        except json.JSONDecodeError as e:
            logger.error("Merge JSON parse error: %s", e)
            return MergeResult(success=False, old_names=old_names, error=f"JSON parse error: {e}")
        except Exception as e:
            logger.error("Merge LLM error: %s", e)
            return MergeResult(success=False, old_names=old_names, error=str(e))
