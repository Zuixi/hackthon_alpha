"""SkillManager -- runtime skill creation, editing, deletion, and merging.

Provides the skill_manage tool for the agent, with automatic similarity
detection and consolidation on create.
"""

import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.agent.skill_engine.consolidator import SkillConsolidator
from app.agent.skill_engine.similarity import SkillSimilarity
from app.agent.skill_engine.usage import UsageTracker
from app.agent.tools.registry import registry, tool_error

logger = logging.getLogger(__name__)

LLMCallFn = Callable[[str], Coroutine[Any, Any, str]]

VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024

SKILL_MANAGE_SCHEMA = {
    "name": "skill_manage",
    "description": (
        "Create, edit, delete, or patch a reusable skill definition. "
        "Skills are operational strategies or workflows that can be applied across sessions.\n\n"
        "Actions:\n"
        "- create: Create a new skill. Will auto-merge with similar existing skills.\n"
        "- edit: Replace a skill's description, triggers, tools, or body entirely.\n"
        "- delete: Archive and remove a skill.\n"
        "- patch: Replace specific text within a skill's body (for fine-tuning).\n\n"
        "Use this when you discover a repeatable pattern worth preserving."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "edit", "delete", "patch"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Skill name (kebab-case, e.g. 'hot-topic-analysis').",
            },
            "description": {
                "type": "string",
                "description": "One-line description of the skill (for create/edit).",
            },
            "triggers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Trigger phrases that activate this skill (for create/edit).",
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tool names this skill uses (for create/edit).",
            },
            "body": {
                "type": "string",
                "description": "Skill instructions in Markdown (for create/edit).",
            },
            "old_text": {
                "type": "string",
                "description": "Text to find and replace (for patch action).",
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text (for patch action).",
            },
        },
        "required": ["action", "name"],
    },
}


def _render_skill_md(name, description, triggers, tools, body):
    """Render a SKILL.md file from components."""
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(f"description: {description}")
    if triggers:
        lines.append("triggers:")
        for t in triggers:
            lines.append(f"  - \"{t}\"")
    if tools:
        lines.append("tools:")
        for t in tools:
            lines.append(f"  - {t}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


class SkillManager:
    """Manages skill lifecycle with similarity detection and auto-merge."""

    def __init__(
        self,
        skills_dir: Path,
        similarity: SkillSimilarity,
        consolidator: SkillConsolidator,
        usage_tracker: UsageTracker,
        skill_loader,
    ):
        self.skills_dir = skills_dir
        self.archive_dir = skills_dir / ".archive"
        self._similarity = similarity
        self._consolidator = consolidator
        self._usage = usage_tracker
        self._loader = skill_loader

    def _validate_name(self, name):
        if not name:
            return "Name is required."
        if len(name) > MAX_NAME_LEN:
            return f"Name too long (max {MAX_NAME_LEN} chars)."
        if not VALID_NAME_RE.match(name):
            return "Name must be kebab-case (lowercase letters, digits, hyphens, dots)."
        return None

    def _skill_dir(self, name):
        return self.skills_dir / name.replace("-", "_")

    def _get_existing_skills_as_dicts(self):
        return [
            {
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
                "tools": s.tools,
                "body": s.body,
            }
            for s in self._loader.list_skills()
        ]

    async def create(self, name, description, triggers, tools, body):
        error = self._validate_name(name)
        if error:
            return {"success": False, "error": error}
        if not description:
            return {"success": False, "error": "Description is required."}
        if len(description) > MAX_DESC_LEN:
            return {"success": False, "error": f"Description too long (max {MAX_DESC_LEN})."}
        if not body:
            return {"success": False, "error": "Body is required."}

        new_skill = {
            "name": name,
            "description": description,
            "triggers": triggers or [],
            "tools": tools or [],
            "body": body,
        }

        existing = self._get_existing_skills_as_dicts()
        similar_results = await self._similarity.find_similar(new_skill, existing)

        if similar_results:
            similar_skills = []
            for r in similar_results:
                for s in existing:
                    if s["name"] == r.skill_name:
                        similar_skills.append(s)
                        break

            all_skills = [new_skill] + similar_skills
            merge_result = await self._consolidator.merge(all_skills)

            if merge_result.success and merge_result.merged_skill:
                merged = merge_result.merged_skill

                for s in similar_skills:
                    self._archive_skill(s["name"])

                self._write_skill(
                    merged["name"], merged["description"],
                    merged["triggers"], merged["tools"], merged["body"],
                )
                self._loader.reload()
                self._usage.on_merge(
                    merged["name"],
                    [s["name"] for s in similar_skills],
                    source="merged",
                )

                return {
                    "success": True,
                    "action": "merged",
                    "name": merged["name"],
                    "merged_from": [s["name"] for s in all_skills],
                    "message": f"Merged {len(all_skills)} similar skills into '{merged['name']}'.",
                }
            else:
                logger.warning("Merge failed: %s. Creating as standalone.", merge_result.error)

        if self._loader.get_skill(name):
            return {"success": False, "error": f"Skill '{name}' already exists. Use 'edit' to modify."}

        self._write_skill(name, description, triggers, tools, body)
        self._loader.reload()
        self._usage.on_create(name, source="extracted")

        return {
            "success": True,
            "action": "created",
            "name": name,
            "message": f"Skill '{name}' created successfully.",
        }

    async def edit(self, name, description=None, triggers=None, tools=None, body=None):
        skill = self._loader.get_skill(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found."}

        new_desc = description if description is not None else skill.description
        new_triggers = triggers if triggers is not None else skill.triggers
        new_tools = tools if tools is not None else skill.tools
        new_body = body if body is not None else skill.body

        self._write_skill(name, new_desc, new_triggers, new_tools, new_body)
        self._loader.reload()

        return {"success": True, "action": "edited", "name": name, "message": f"Skill '{name}' updated."}

    async def delete(self, name):
        skill = self._loader.get_skill(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found."}

        self._archive_skill(name)
        self._loader.reload()
        self._usage.on_delete(name)

        return {"success": True, "action": "deleted", "name": name, "message": f"Skill '{name}' archived and removed."}

    async def patch(self, name, old_text, new_text):
        skill = self._loader.get_skill(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found."}
        if not old_text:
            return {"success": False, "error": "old_text is required for patch."}

        if old_text not in skill.body:
            return {"success": False, "error": f"old_text not found in skill '{name}'."}

        new_body = skill.body.replace(old_text, new_text, 1)
        self._write_skill(name, skill.description, skill.triggers, skill.tools, new_body)
        self._loader.reload()

        return {"success": True, "action": "patched", "name": name, "message": f"Skill '{name}' patched."}

    def _write_skill(self, name, description, triggers, tools, body):
        skill_dir = self._skill_dir(name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = _render_skill_md(name, description, triggers, tools, body)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def _archive_skill(self, name):
        skill_dir = self._skill_dir(name)
        if not skill_dir.exists():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"{name}_{int(time.time())}"
        dest = self.archive_dir / archive_name
        shutil.move(str(skill_dir), str(dest))
        logger.info("Archived skill '%s' -> %s", name, dest)


def register_skill_manage_tool(skill_manager):
    """Register the skill_manage tool into the global registry."""

    async def _handler(args):
        action = args.get("action", "")
        name = args.get("name", "")

        if action == "create":
            result = await skill_manager.create(
                name=name,
                description=args.get("description", ""),
                triggers=args.get("triggers", []),
                tools=args.get("tools", []),
                body=args.get("body", ""),
            )
        elif action == "edit":
            result = await skill_manager.edit(
                name=name,
                description=args.get("description"),
                triggers=args.get("triggers"),
                tools=args.get("tools"),
                body=args.get("body"),
            )
        elif action == "delete":
            result = await skill_manager.delete(name=name)
        elif action == "patch":
            result = await skill_manager.patch(
                name=name,
                old_text=args.get("old_text", ""),
                new_text=args.get("new_text", ""),
            )
        else:
            return tool_error(f"Unknown action '{action}'.")

        return json.dumps(result, ensure_ascii=False)

    registry.register(
        name="skill_manage",
        schema=SKILL_MANAGE_SCHEMA,
        handler=_handler,
        is_async=True,
    )
