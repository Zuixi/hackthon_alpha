"""Tests for the skill engine: similarity, usage tracking, consolidator, extractor."""

import json
import tempfile
from pathlib import Path

import pytest

from app.agent.skill_engine.similarity import (
    trigger_jaccard,
    tfidf_cosine,
    SkillSimilarity,
)
from app.agent.skill_engine.usage import UsageTracker
from app.agent.skill_engine.consolidator import SkillConsolidator
from app.agent.skill_engine.extractor import SkillExtractor


# ── Trigger Jaccard ──────────────────────────────────────────

class TestTriggerJaccard:
    def test_identical_sets(self):
        score = trigger_jaccard(["a", "b", "c"], ["a", "b", "c"])
        assert score == 1.0

    def test_disjoint_sets(self):
        score = trigger_jaccard(["a", "b"], ["c", "d"])
        assert score == 0.0

    def test_partial_overlap(self):
        score = trigger_jaccard(["热榜", "热点", "趋势"], ["热榜", "热门话题", "趋势"])
        assert 0.4 < score < 0.6

    def test_empty_sets(self):
        assert trigger_jaccard([], ["a"]) == 0.0
        assert trigger_jaccard(["a"], []) == 0.0
        assert trigger_jaccard([], []) == 0.0

    def test_case_insensitive(self):
        score = trigger_jaccard(["Hello", "World"], ["hello", "world"])
        assert score == 1.0


# ── TF-IDF Cosine ───────────────────────────────────────────

class TestTFIDFCosine:
    def test_similar_texts(self):
        score = tfidf_cosine(
            "帮助创作者发现和分析知乎热点话题",
            "帮助创作者分析热门话题并找到选题",
        )
        assert score > 0.2

    def test_unrelated_texts(self):
        score = tfidf_cosine(
            "帮助创作者发布内容到知乎",
            "分析股市行情和投资策略",
        )
        assert score < 0.2

    def test_identical_texts(self):
        text = "知乎热点话题分析工作流"
        score = tfidf_cosine(text, text)
        assert score > 0.95

    def test_empty_text(self):
        assert tfidf_cosine("", "hello") == 0.0
        assert tfidf_cosine("hello", "") == 0.0


# ── SkillSimilarity (without LLM layer) ────────────────────

class TestSkillSimilarity:
    @pytest.mark.asyncio
    async def test_no_similar_skills(self):
        sim = SkillSimilarity(trigger_threshold=0.3, tfidf_threshold=0.5)
        new_skill = {
            "name": "new-skill",
            "description": "A brand new unique skill",
            "triggers": ["unique-trigger-xyz"],
            "tools": [],
            "body": "Completely unrelated content about quantum physics",
        }
        existing = [
            {
                "name": "existing",
                "description": "Help with cooking recipes",
                "triggers": ["recipe", "cook"],
                "tools": [],
                "body": "Step 1: Preheat oven. Step 2: Mix ingredients.",
            }
        ]
        results = await sim.find_similar(new_skill, existing)
        assert results == []

    @pytest.mark.asyncio
    async def test_trigger_overlap_detected(self):
        sim = SkillSimilarity(trigger_threshold=0.3, tfidf_threshold=0.5)
        new_skill = {
            "name": "hot-analysis-v2",
            "description": "分析热点",
            "triggers": ["热榜", "热点", "趋势"],
            "tools": [],
            "body": "热点分析工作流",
        }
        existing = [
            {
                "name": "hotspot_analysis",
                "description": "热点分析",
                "triggers": ["热榜", "热门话题", "趋势"],
                "tools": [],
                "body": "分析知乎热榜",
            }
        ]
        results = await sim.find_similar(new_skill, existing)
        assert len(results) >= 1
        assert results[0].skill_name == "hotspot_analysis"
        assert results[0].pre_method == "trigger_jaccard"

    @pytest.mark.asyncio
    async def test_empty_existing(self):
        sim = SkillSimilarity()
        results = await sim.find_similar({"name": "x"}, [])
        assert results == []


# ── UsageTracker ─────────────────────────────────────────────

class TestUsageTracker:
    def test_on_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_create("test-skill", "manual")
            stats = tracker.get_stats("test-skill")
            assert stats is not None
            assert stats["source"] == "manual"
            assert stats["created_at"] is not None

    def test_on_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_view("s1")
            tracker.on_view("s1")
            assert tracker.get_stats("s1")["views"] == 2

    def test_on_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_use("s1")
            assert tracker.get_stats("s1")["uses"] == 1
            assert tracker.get_stats("s1")["last_used_at"] is not None

    def test_on_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_create("s1", "manual")
            tracker.on_delete("s1")
            assert tracker.get_stats("s1") is None

    def test_on_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_create("a", "manual")
            tracker.on_view("a")
            tracker.on_view("a")
            tracker.on_create("b", "manual")
            tracker.on_view("b")

            tracker.on_merge("merged", ["a", "b"], source="merged")

            assert tracker.get_stats("a") is None
            assert tracker.get_stats("b") is None
            merged = tracker.get_stats("merged")
            assert merged is not None
            assert merged["views"] == 3
            assert merged["source"] == "merged"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".usage.json"
            t1 = UsageTracker(path)
            t1.on_create("skill1", "extracted")
            t1.on_view("skill1")

            t2 = UsageTracker(path)
            stats = t2.get_stats("skill1")
            assert stats is not None
            assert stats["views"] == 1
            assert stats["source"] == "extracted"

    def test_get_all_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / ".usage.json")
            tracker.on_create("a", "manual")
            tracker.on_create("b", "extracted")
            all_stats = tracker.get_all_stats()
            assert "a" in all_stats
            assert "b" in all_stats


# ── SkillConsolidator ────────────────────────────────────────

class TestSkillConsolidator:
    @pytest.mark.asyncio
    async def test_single_skill(self):
        consolidator = SkillConsolidator()
        skill = {"name": "only-one", "description": "d", "triggers": [], "tools": [], "body": "b"}
        result = await consolidator.merge([skill])
        assert result.success
        assert result.merged_skill["name"] == "only-one"

    @pytest.mark.asyncio
    async def test_empty_list(self):
        consolidator = SkillConsolidator()
        result = await consolidator.merge([])
        assert not result.success

    @pytest.mark.asyncio
    async def test_no_llm_configured(self):
        consolidator = SkillConsolidator(llm_call=None)
        skills = [
            {"name": "a", "description": "d1", "triggers": [], "tools": [], "body": "b1"},
            {"name": "b", "description": "d2", "triggers": [], "tools": [], "body": "b2"},
        ]
        result = await consolidator.merge(skills)
        assert not result.success
        assert "not configured" in result.error


# ── SkillExtractor ───────────────────────────────────────────

class TestSkillExtractor:
    @pytest.mark.asyncio
    async def test_no_llm(self):
        extractor = SkillExtractor(llm_call=None)
        result = await extractor.extract_from_messages([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ], [])
        assert result == []

    @pytest.mark.asyncio
    async def test_short_session(self):
        async def mock_llm(prompt):
            return '{"skills": []}'

        extractor = SkillExtractor(llm_call=mock_llm)
        result = await extractor.extract_from_messages([
            {"role": "user", "content": "Hi"},
        ], [])
        assert result == []

    @pytest.mark.asyncio
    async def test_extraction_with_mock_llm(self):
        mock_response = json.dumps({
            "skills": [{
                "name": "test-workflow",
                "description": "A test workflow",
                "triggers": ["test"],
                "tools": ["tool1"],
                "body": "## Steps\n\n1. Do this\n2. Do that",
            }]
        })

        async def mock_llm(prompt):
            return mock_response

        extractor = SkillExtractor(llm_call=mock_llm)
        messages = [
            {"role": "user", "content": "Help me analyze hot topics"},
            {"role": "assistant", "content": "Let me search for you. I found..."},
            {"role": "user", "content": "Now help me write about it"},
            {"role": "assistant", "content": "Here's a draft based on the analysis..."},
            {"role": "user", "content": "Polish and publish"},
            {"role": "assistant", "content": "Done! Published successfully."},
        ]
        result = await extractor.extract_from_messages(messages, [])
        assert len(result) == 1
        assert result[0]["name"] == "test-workflow"
        assert result[0]["description"] == "A test workflow"

    @pytest.mark.asyncio
    async def test_extraction_returns_empty(self):
        async def mock_llm(prompt):
            return '{"skills": []}'

        extractor = SkillExtractor(llm_call=mock_llm)
        messages = [
            {"role": "user", "content": "What time is it?"},
            {"role": "assistant", "content": "I don't have a clock."},
            {"role": "user", "content": "Ok thanks"},
            {"role": "assistant", "content": "You're welcome!"},
        ]
        result = await extractor.extract_from_messages(messages, [])
        assert result == []
