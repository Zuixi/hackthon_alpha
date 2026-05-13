"""Skill loader and skill tools.

Scans SKILL.md files from the skills directory, parses YAML frontmatter,
and provides skills_list / skill_view tools for the agent.
Supports dynamic reload for runtime skill creation/deletion.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.tools.registry import registry

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    body: str = ""
    path: str = ""


def _parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a SKILL.md file. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    frontmatter = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    metadata = {}
    current_key = None
    current_list: Optional[List[str]] = None

    for line in frontmatter.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        if line.startswith("  - ") and current_key:
            value = line[4:].strip().strip('"').strip("'")
            if current_list is not None:
                current_list.append(value)
            continue

        match = re.match(r'^(\w+)\s*:\s*(.*)', line)
        if match:
            key = match.group(1)
            value = match.group(2).strip().strip('"').strip("'")
            if value:
                metadata[key] = value
                current_key = key
                current_list = None
            else:
                metadata[key] = []
                current_key = key
                current_list = metadata[key]

    return metadata, body


class SkillLoader:
    """Loads and manages SKILL.md skill definitions with dynamic reload."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._skills: Dict[str, SkillInfo] = {}
        self._usage_tracker = None

    def set_usage_tracker(self, tracker) -> None:
        self._usage_tracker = tracker

    def load_skills(self) -> None:
        """Scan skills directory and load all SKILL.md files."""
        self._skills.clear()
        if not self.skills_dir.exists():
            logger.info("Skills directory not found: %s", self.skills_dir)
            return

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                metadata, body = _parse_yaml_frontmatter(content)

                name = metadata.get("name", skill_dir.name)
                skill = SkillInfo(
                    name=name,
                    description=metadata.get("description", ""),
                    triggers=metadata.get("triggers", []),
                    tools=metadata.get("tools", []),
                    body=body,
                    path=str(skill_file),
                )
                self._skills[name] = skill
            except Exception as e:
                logger.error("Failed to load skill from %s: %s", skill_file, e)

        logger.info("Loaded %d skill(s)", len(self._skills))

    def reload(self) -> None:
        """Reload all skills from disk (call after create/delete/merge)."""
        self.load_skills()

    def get_skill(self, name: str) -> Optional[SkillInfo]:
        return self._skills.get(name)

    def list_skills(self) -> List[SkillInfo]:
        return list(self._skills.values())

    def skill_names(self) -> List[str]:
        return list(self._skills.keys())

    def build_skill_summary(self) -> str:
        """Build a concise skill summary for the system prompt."""
        if not self._skills:
            return ""

        parts = ["## Available Skills"]
        for skill in self._skills.values():
            triggers = ", ".join(f'"{t}"' for t in skill.triggers[:3])
            parts.append(f"- **{skill.name}**: {skill.description}")
            if triggers:
                parts.append(f"  Triggers: {triggers}")
        parts.append(
            "\nUse `skills_list` for details, `skill_view` to see full instructions, "
            "or `skill_manage` to create/edit/delete skills."
        )
        return "\n".join(parts)


SKILLS_LIST_SCHEMA = {
    "name": "skills_list",
    "description": "List all available skills with their descriptions, triggers, and usage stats.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

SKILL_VIEW_SCHEMA = {
    "name": "skill_view",
    "description": "View the full instructions of a specific skill by name.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The skill name to view.",
            },
        },
        "required": ["name"],
    },
}


def register_skill_tools(skill_loader: SkillLoader) -> None:
    """Register skill-related tools into the global registry."""

    async def _list_handler(args: Dict[str, Any]) -> str:
        skills = skill_loader.list_skills()
        if not skills:
            return json.dumps({"message": "No skills available.", "skills": []})
        result = []
        for s in skills:
            entry = {
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
                "tools": s.tools,
            }
            if skill_loader._usage_tracker:
                stats = skill_loader._usage_tracker.get_stats(s.name)
                if stats:
                    entry["views"] = stats.get("views", 0)
                    entry["uses"] = stats.get("uses", 0)
                    entry["source"] = stats.get("source", "manual")
            result.append(entry)
        return json.dumps({"skills": result}, ensure_ascii=False)

    async def _view_handler(args: Dict[str, Any]) -> str:
        name = args.get("name", "")
        skill = skill_loader.get_skill(name)
        if not skill:
            available = [s.name for s in skill_loader.list_skills()]
            return json.dumps({
                "error": f"Skill '{name}' not found.",
                "available": available,
            }, ensure_ascii=False)

        if skill_loader._usage_tracker:
            skill_loader._usage_tracker.on_view(name)

        return json.dumps({
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.body,
            "tools": skill.tools,
        }, ensure_ascii=False)

    registry.register(name="skills_list", schema=SKILLS_LIST_SCHEMA, handler=_list_handler)
    registry.register(name="skill_view", schema=SKILL_VIEW_SCHEMA, handler=_view_handler)
