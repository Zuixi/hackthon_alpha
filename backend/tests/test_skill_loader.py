"""Tests for SkillLoader and skill file parsing."""

import tempfile
from pathlib import Path

from app.agent.tools.skill_tool import SkillLoader, _parse_yaml_frontmatter


class TestParseYamlFrontmatter:
    def test_basic_frontmatter(self):
        content = """---
name: test-skill
description: A test skill
triggers:
  - "hello"
  - "world"
tools:
  - tool_a
  - tool_b
---

## Instructions

Do something useful."""

        metadata, body = _parse_yaml_frontmatter(content)
        assert metadata["name"] == "test-skill"
        assert metadata["description"] == "A test skill"
        assert metadata["triggers"] == ["hello", "world"]
        assert metadata["tools"] == ["tool_a", "tool_b"]
        assert "## Instructions" in body

    def test_no_frontmatter(self):
        content = "Just plain text."
        metadata, body = _parse_yaml_frontmatter(content)
        assert metadata == {}
        assert body == "Just plain text."

    def test_empty_content(self):
        metadata, body = _parse_yaml_frontmatter("")
        assert metadata == {}
        assert body == ""


class TestSkillLoader:
    def test_load_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            skill_dir = skills_dir / "my_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: Test skill
triggers:
  - "trigger1"
tools:
  - tool_x
---

## Workflow

Step 1: Do X.""", encoding="utf-8")

            loader = SkillLoader(skills_dir)
            loader.load_skills()

            skills = loader.list_skills()
            assert len(skills) == 1
            assert skills[0].name == "my-skill"
            assert skills[0].description == "Test skill"
            assert skills[0].triggers == ["trigger1"]
            assert skills[0].tools == ["tool_x"]

    def test_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            loader = SkillLoader(skills_dir)
            loader.load_skills()
            assert len(loader.list_skills()) == 0

            skill_dir = skills_dir / "new_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: new-skill
description: Added later
---

Content.""", encoding="utf-8")

            loader.reload()
            assert len(loader.list_skills()) == 1
            assert loader.get_skill("new-skill") is not None

    def test_skip_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            archive_dir = skills_dir / ".archive"
            archive_dir.mkdir()
            (archive_dir / "SKILL.md").write_text("---\nname: archived\n---\n", encoding="utf-8")

            loader = SkillLoader(skills_dir)
            loader.load_skills()
            assert len(loader.list_skills()) == 0

    def test_get_skill_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            loader = SkillLoader(Path(tmp))
            loader.load_skills()
            assert loader.get_skill("nonexistent") is None

    def test_skill_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            for name in ["alpha", "beta"]:
                d = skills_dir / name
                d.mkdir()
                (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\n", encoding="utf-8")

            loader = SkillLoader(skills_dir)
            loader.load_skills()
            names = loader.skill_names()
            assert sorted(names) == ["alpha", "beta"]

    def test_build_skill_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            d = skills_dir / "test"
            d.mkdir()
            (d / "SKILL.md").write_text("""---
name: test
description: A test skill
triggers:
  - "hello"
---

Body.""", encoding="utf-8")

            loader = SkillLoader(skills_dir)
            loader.load_skills()
            summary = loader.build_skill_summary()
            assert "test" in summary
            assert "A test skill" in summary
            assert "skill_manage" in summary
