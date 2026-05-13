"""Tests for agent core optimization modules:
  - tool argument repair & coercion
  - tool guardrails
  - token usage tracker
  - compressor Anthropic format handling
"""

import json
import pytest

from app.agent.tools.registry import repair_tool_args, coerce_tool_args
from app.agent.tool_guardrails import ToolGuardrails
from app.agent.token_tracker import TokenUsageTracker
from app.agent.context.compressor import (
    ContextCompressor,
    _estimate_messages_tokens,
    _extract_tool_uses,
    _extract_tool_results,
    _content_char_count,
)


# ===== repair_tool_args =====

class TestRepairToolArgs:
    def test_valid_json_passthrough(self):
        raw = '{"query": "hello", "limit": 10}'
        assert json.loads(repair_tool_args(raw)) == {"query": "hello", "limit": 10}

    def test_trailing_comma(self):
        raw = '{"query": "hello", "limit": 10,}'
        result = repair_tool_args(raw)
        assert json.loads(result) == {"query": "hello", "limit": 10}

    def test_unclosed_brace(self):
        raw = '{"query": "hello"'
        result = repair_tool_args(raw)
        assert json.loads(result) == {"query": "hello"}

    def test_unclosed_bracket(self):
        raw = '{"items": [1, 2, 3'
        result = repair_tool_args(raw)
        parsed = json.loads(result)
        assert parsed["items"] == [1, 2, 3]

    def test_empty_string(self):
        assert repair_tool_args("") == "{}"
        assert repair_tool_args("  ") == "{}"

    def test_single_quotes(self):
        raw = "{'query': 'hello'}"
        result = repair_tool_args(raw)
        assert json.loads(result) == {"query": "hello"}


# ===== coerce_tool_args =====

class TestCoerceToolArgs:
    def test_string_to_int(self):
        schema = {"properties": {"limit": {"type": "integer"}}}
        result = coerce_tool_args({"limit": "10"}, schema)
        assert result["limit"] == 10

    def test_string_to_float(self):
        schema = {"properties": {"score": {"type": "number"}}}
        result = coerce_tool_args({"score": "3.14"}, schema)
        assert result["score"] == 3.14

    def test_string_to_bool(self):
        schema = {"properties": {"active": {"type": "boolean"}}}
        result = coerce_tool_args({"active": "true"}, schema)
        assert result["active"] is True

    def test_int_to_string(self):
        schema = {"properties": {"name": {"type": "string"}}}
        result = coerce_tool_args({"name": 42}, schema)
        assert result["name"] == "42"

    def test_no_schema(self):
        result = coerce_tool_args({"x": "y"}, {})
        assert result == {"x": "y"}

    def test_missing_key_ignored(self):
        schema = {"properties": {"limit": {"type": "integer"}}}
        result = coerce_tool_args({"query": "hello"}, schema)
        assert result == {"query": "hello"}


# ===== ToolGuardrails =====

class TestToolGuardrails:
    def test_no_trigger_on_unique_calls(self):
        g = ToolGuardrails(max_repeat=3)
        for i in range(5):
            msg = g.check_before_execute("tool_a", {"query": f"q{i}"})
            assert msg is None

    def test_repeat_detection(self):
        g = ToolGuardrails(max_repeat=3)
        args = {"query": "same"}
        assert g.check_before_execute("tool_a", args) is None
        assert g.check_before_execute("tool_a", args) is None
        assert g.check_before_execute("tool_a", args) is None
        msg = g.check_before_execute("tool_a", args)
        assert msg is not None
        assert "infinite loop" in msg.lower() or "same args" in msg.lower()

    def test_consecutive_error_circuit_breaker(self):
        g = ToolGuardrails(max_consecutive_errors=3)
        g.record_error()
        g.record_error()
        g.record_error()
        msg = g.check_before_execute("any_tool", {})
        assert msg is not None
        assert "consecutive errors" in msg.lower() or "halted" in msg.lower()

    def test_success_resets_error_count(self):
        g = ToolGuardrails(max_consecutive_errors=3)
        g.record_error()
        g.record_error()
        g.record_success()
        g.record_error()
        g.record_error()
        msg = g.check_before_execute("any_tool", {})
        assert msg is None

    def test_reset(self):
        g = ToolGuardrails(max_repeat=2)
        g.check_before_execute("t", {"a": 1})
        g.check_before_execute("t", {"a": 1})
        g.record_error()
        g.reset()
        assert g.check_before_execute("t", {"a": 1}) is None


# ===== TokenUsageTracker =====

class TestTokenUsageTracker:
    def test_empty_summary(self):
        t = TokenUsageTracker()
        s = t.summary()
        assert s["turns"] == 0
        assert s["total_tokens"] == 0

    def test_single_turn(self):
        t = TokenUsageTracker()
        t.new_turn("model-x")
        t.record_usage({"prompt_tokens": 100, "completion_tokens": 50})
        t.record_tool_call()
        t.record_tool_call()
        s = t.summary()
        assert s["turns"] == 1
        assert s["total_input_tokens"] == 100
        assert s["total_output_tokens"] == 50
        assert s["total_tokens"] == 150
        assert s["total_tool_calls"] == 2

    def test_multi_turn(self):
        t = TokenUsageTracker()
        t.new_turn("m")
        t.record_usage({"prompt_tokens": 100, "completion_tokens": 20})
        t.new_turn("m")
        t.record_usage({"prompt_tokens": 200, "completion_tokens": 30})
        s = t.summary()
        assert s["turns"] == 2
        assert s["total_input_tokens"] == 300
        assert s["total_output_tokens"] == 50

    def test_cache_hit_rate(self):
        t = TokenUsageTracker()
        t.new_turn("m")
        t.record_usage({"prompt_tokens": 100, "completion_tokens": 10, "cache_read_tokens": 80})
        s = t.summary()
        assert s["cache_hit_rate"] == 80.0


# ===== Compressor Anthropic Format =====

class TestCompressorAnthropicFormat:
    def _make_anthropic_messages(self):
        """Create a realistic Anthropic-format conversation."""
        return [
            {"role": "user", "content": [{"type": "text", "text": "Hello, search for AI topics"}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Let me search for you."},
                {"type": "tool_use", "id": "tu_1", "name": "zhihu_search", "input": {"query": "AI"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "Result content " * 100},
            ]},
            {"role": "assistant", "content": [{"type": "text", "text": "Here are the results..."}]},
            {"role": "user", "content": [{"type": "text", "text": "Tell me more"}]},
        ]

    def test_extract_tool_uses(self):
        msgs = self._make_anthropic_messages()
        uses = _extract_tool_uses(msgs[1])
        assert len(uses) == 1
        assert uses[0]["name"] == "zhihu_search"

    def test_extract_tool_results(self):
        msgs = self._make_anthropic_messages()
        results = _extract_tool_results(msgs[2])
        assert len(results) == 1
        assert results[0]["tool_use_id"] == "tu_1"

    def test_content_char_count_str(self):
        assert _content_char_count("hello") == 5

    def test_content_char_count_list(self):
        content = [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]
        assert _content_char_count(content) == 10

    def test_estimate_tokens_anthropic(self):
        msgs = self._make_anthropic_messages()
        tokens = _estimate_messages_tokens(msgs)
        assert tokens > 0

    def test_sanitize_orphan_tool_result(self):
        c = ContextCompressor(context_length=100000)
        msgs = [
            {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "orphan_1", "content": "orphaned result"},
            ]},
            {"role": "assistant", "content": [{"type": "text", "text": "bye"}]},
        ]
        sanitized = c._sanitize_tool_pairs(msgs)
        all_result_ids = set()
        for m in sanitized:
            for tr in _extract_tool_results(m):
                all_result_ids.add(tr["tool_use_id"])
        assert "orphan_1" not in all_result_ids

    def test_sanitize_missing_result_adds_stub(self):
        c = ContextCompressor(context_length=100000)
        msgs = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "calling"},
                {"type": "tool_use", "id": "tu_99", "name": "test_tool", "input": {}},
            ]},
            {"role": "assistant", "content": [{"type": "text", "text": "done"}]},
        ]
        sanitized = c._sanitize_tool_pairs(msgs)
        all_result_ids = set()
        for m in sanitized:
            for tr in _extract_tool_results(m):
                all_result_ids.add(tr["tool_use_id"])
        assert "tu_99" in all_result_ids
