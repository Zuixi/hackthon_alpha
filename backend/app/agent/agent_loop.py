"""AgentLoop — ReAct loop integrating all subsystems.

Replaces the original agent_service.py with a full-featured agent that
includes memory, session tracking, context compression, skills, MCP, and
multi-provider transport support.

Enhanced with:
  - Stream retry & empty-response recovery
  - Tool argument repair & type coercion
  - Tool call guardrails (loop detection, error circuit breaker)
  - Parallel tool execution for read-only tools
  - Graceful degradation at max iterations
  - Tool result size management with persist/preview
  - System prompt layered caching (stable/context/volatile)
  - Token usage tracking
"""

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.agent import config as agent_config
from app.agent.context.compressor import ContextCompressor
from app.agent.memory.memory_manager import MemoryManager
from app.agent.memory.memory_reviewer import MemoryReviewer
from app.agent.mcp.client import register_mcp_servers, shutdown_mcp_servers
from app.agent.mcp.config import load_mcp_config
from app.agent.session.session_db import SessionDB
from app.agent.skill_engine.consolidator import SkillConsolidator
from app.agent.skill_engine.extractor import SkillExtractor
from app.agent.skill_engine.similarity import SkillSimilarity
from app.agent.skill_engine.usage import UsageTracker
from app.agent.token_tracker import TokenUsageTracker
from app.agent.tool_guardrails import ToolGuardrails
from app.agent.tools.memory_tool import BuiltinMemoryProvider, register_memory_tool
from app.agent.tools.registry import (
    ToolRegistry,
    coerce_tool_args,
    registry,
    repair_tool_args,
)
from app.agent.tools.session_search import register_session_search_tool
from app.agent.tools.skill_manager import SkillManager, register_skill_manage_tool
from app.agent.tools.skill_tool import SkillLoader, register_skill_tools
from app.agent.tools.card_tools import register_card_tools
from app.agent.tools.social_tools import register_social_tools
from app.agent.tools.zhihu_tools import register_zhihu_tools
from app.agent.transports import get_transport

logger = logging.getLogger(__name__)

# Read-only tools safe for parallel execution
PARALLEL_SAFE_TOOLS = frozenset({
    "zhihu_hot_list", "zhihu_search", "zhihu_global_search",
    "zhihu_direct_answer", "zhihu_get_ring_detail",
    "zhihu_story_list", "zhihu_story_detail",
    "session_search", "skills_list", "skill_view",
    "list_idea_cards", "get_follower_stats", "get_followee_list",
    "get_recent_moments", "hot_topics_multiplatform", "hot_topics_grouped",
})

# ---------------------------------------------------------------------------
# System prompt sections — split for prefix caching
# ---------------------------------------------------------------------------

_STABLE_PROMPT = """你是「灵感引擎」—— 一位资深的知乎创作者 AI 助手。

## 你的角色
你是一个深谙内容创作之道的 AI 助手，专门帮助知乎创作者发现热点、激发灵感、打磨内容、发布作品。你不是一个通用聊天机器人，而是一个懂内容、懂传播、懂知乎生态的专业创作伙伴。

## 你的能力
你可以通过工具调用来：
1. **发现热点**：获取知乎实时热榜，分析当前热门话题和趋势
2. **深度调研**：搜索知乎站内和全网内容，收集创作素材和参考观点
3. **知识问答**：调用知乎直答Agent，获取基于知乎优质内容的专业回答
4. **社区互动**：浏览知乎圈子动态，了解社区讨论风向
5. **内容发布**：帮助用户将创作内容发布到知乎圈子
6. **故事素材**：获取知乎故事库内容，为创意写作提供灵感
7. **记忆管理**：记住用户的偏好、创作风格和历史讨论
8. **历史回忆**：搜索过去的对话记录，回顾之前的讨论
9. **灵感管理**：将有价值的洞察保存为灵感卡片，随时回顾和检索
10. **社交洞察**：分析粉丝增长趋势、查看关注列表、获取关注动态
11. **跨平台热点**：获取微博、B站、抖音、头条等多平台热点，进行跨平台对比分析

## 你的工作方式
- 主动使用工具获取信息，而不是凭空回答
- 给出有深度、有洞察的分析，而非泛泛而谈
- 提供多个创作切入角度供用户选择
- 结合知乎平台特点给出内容建议
- 在用户确认前，不要直接发布内容
- 主动记住用户的偏好和创作习惯（使用 memory 工具）
- 当用户获得有价值的创作洞察时，主动建议保存为灵感卡片
- 结合粉丝数据和热点趋势给出内容策略建议
- 善用跨平台热点对比，发现内容机会和差异化切入点

## 你的风格
- 专业但不刻板，有网感但不浮躁
- 善于发现话题的独特角度
- 重视论据和数据支撑
- 语言简洁有力，信息密度高"""


_MEMORY_CONTEXT_TAG_RE = re.compile(r"</?memory-context>")


class AgentLoop:
    """Full-featured ReAct agent loop with all subsystems integrated."""

    def __init__(self):
        self._initialized = False
        self._current_user_id: Optional[str] = None
        self._tool_registry = registry
        self._memory_manager = MemoryManager()
        self._session_db: Optional[SessionDB] = None
        self._compressor: Optional[ContextCompressor] = None
        self._skill_loader: Optional[SkillLoader] = None
        self._memory_provider: Optional[BuiltinMemoryProvider] = None
        self._skill_manager: Optional[SkillManager] = None
        self._skill_extractor: Optional[SkillExtractor] = None
        self._memory_reviewer: Optional[MemoryReviewer] = None
        self._usage_tracker: Optional[UsageTracker] = None
        self._turns_since_memory_use = 0

    def initialize(
        self,
        user_id: str = "default",
        zhihu_token: str = "",
        session_id: str = "",
    ) -> None:
        """Initialize all subsystems. Call once at startup or per-user."""
        if self._initialized and self._current_user_id == user_id:
            register_card_tools(user_id, session_id)
            register_social_tools(user_id, zhihu_token)
            return
        if self._initialized and self._current_user_id != user_id:
            self._reload_memory_for_user(user_id)
            register_card_tools(user_id, session_id)
            register_social_tools(user_id, zhihu_token)
            return

        data_dir = agent_config.AGENT_DATA_DIR
        data_dir.mkdir(parents=True, exist_ok=True)

        # Tool Registry — register zhihu tools (including multiplatform)
        register_zhihu_tools()

        # Card & social tools (re-registered per call with user context)
        register_card_tools(user_id, session_id)
        register_social_tools(user_id, zhihu_token)

        # Memory system
        memory_dir = data_dir / "memories" / user_id
        self._memory_provider = register_memory_tool(
            memory_dir,
            memory_char_limit=agent_config.MEMORY_CHAR_LIMIT,
            user_char_limit=agent_config.USER_CHAR_LIMIT,
        )
        self._memory_manager.add_provider(self._memory_provider)
        self._memory_manager.initialize_all(session_id="", user_id=user_id)

        # Session DB
        self._session_db = SessionDB(data_dir / "sessions.db")

        # Session search tool
        register_session_search_tool(self._session_db)

        # Skill loader + engine
        skills_dir = Path(__file__).parent / "skills"
        self._skill_loader = SkillLoader(skills_dir)
        self._skill_loader.load_skills()

        # Usage tracker
        self._usage_tracker = UsageTracker(skills_dir / ".usage.json")
        self._skill_loader.set_usage_tracker(self._usage_tracker)

        # Register read-only skill tools
        register_skill_tools(self._skill_loader)

        # Skill engine (similarity, consolidation, extraction)
        llm_call = self._call_llm_for_summary

        similarity = SkillSimilarity(
            trigger_threshold=0.3,
            tfidf_threshold=0.5,
            llm_threshold=agent_config.SKILL_SIMILARITY_THRESHOLD,
            llm_call=llm_call,
        )
        consolidator = SkillConsolidator(llm_call=llm_call)

        self._skill_manager = SkillManager(
            skills_dir=skills_dir,
            similarity=similarity,
            consolidator=consolidator,
            usage_tracker=self._usage_tracker,
            skill_loader=self._skill_loader,
        )
        register_skill_manage_tool(self._skill_manager)

        self._skill_extractor = SkillExtractor(llm_call=llm_call)
        self._memory_reviewer = MemoryReviewer(llm_call=llm_call)

        # Context compressor
        self._compressor = ContextCompressor(
            context_length=128000,
            threshold_percent=0.50,
            summarize_fn=llm_call,
        )

        # MCP servers
        mcp_config = load_mcp_config(agent_config.MCP_SERVERS_CONFIG)
        if mcp_config:
            register_mcp_servers(mcp_config, self._tool_registry)

        self._initialized = True
        self._current_user_id = user_id
        logger.info(
            "AgentLoop initialized: %d tools, %d skills",
            len(self._tool_registry.tool_names),
            len(self._skill_loader.list_skills()) if self._skill_loader else 0,
        )

    def _reload_memory_for_user(self, user_id: str) -> None:
        """Rebuild memory store for a different user without re-registering tools."""
        data_dir = agent_config.AGENT_DATA_DIR
        memory_dir = data_dir / "memories" / user_id
        if self._memory_provider:
            self._memory_provider.reload_for_user(memory_dir)
        self._current_user_id = user_id
        self._turns_since_memory_use = 0
        logger.info("Memory reloaded for user %s", user_id)

    async def _call_llm_for_summary(self, prompt: str) -> str:
        """Call LLM for context compression summary."""
        transport = get_transport(agent_config.get_transport_mode())
        if not transport:
            return ""

        kwargs = transport.build_kwargs(
            model=agent_config.LLM_MODEL,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            system="You are a summarization agent. Produce only the summary.",
            max_tokens=4096,
            temperature=0.3,
        )

        parts = []
        async for event in transport.stream_api(
            api_key=agent_config.LLM_API_KEY,
            base_url=agent_config.LLM_BASE_URL,
            kwargs=kwargs,
        ):
            if event.get("type") == "text_delta":
                parts.append(event.get("content", ""))
            elif event.get("type") == "error":
                logger.error("Summary LLM error: %s", event.get("message"))
                return ""
        return "".join(parts)

    # ------------------------------------------------------------------
    # System prompt: layered for prefix caching
    # ------------------------------------------------------------------

    def _build_system_prompt_sections(
        self, topic_title: str = "", search_context: str = ""
    ) -> Dict[str, str]:
        """Return system prompt split into stable / context / volatile."""
        # Context section (changes per session — skills + topic)
        context_parts = []
        if self._skill_loader:
            summary = self._skill_loader.build_skill_summary()
            if summary:
                context_parts.append(summary)
        if topic_title:
            context_parts.append(f"\n## 当前话题\n用户正在围绕「{topic_title}」进行创作探讨。")
        if search_context:
            context_parts.append(f"\n## 参考资料\n{search_context}")
        if not context_parts:
            context_parts.append("\n用户正在进行自由创作探索。")

        # Volatile section (changes every turn — memory + nudge + timestamp)
        volatile_parts = []
        mem_prompt = self._memory_manager.build_system_prompt()
        if mem_prompt:
            volatile_parts.append(mem_prompt)

        return {
            "stable": _STABLE_PROMPT,
            "context": "\n".join(context_parts),
            "volatile": "\n".join(volatile_parts),
        }

    @staticmethod
    def _format_system_for_transport(
        sections: Dict[str, str], transport_mode: str
    ) -> Any:
        """Format system prompt for the transport.

        For Anthropic-compatible transports: returns a list of text blocks
        with cache_control on the stable section.
        For ChatCompletions: returns a concatenated string.
        """
        if transport_mode == "minimax_anthropic":
            blocks = []
            if sections["stable"]:
                blocks.append({
                    "type": "text",
                    "text": sections["stable"],
                    "cache_control": {"type": "ephemeral"},
                })
            if sections["context"]:
                blocks.append({"type": "text", "text": sections["context"]})
            if sections["volatile"]:
                blocks.append({"type": "text", "text": sections["volatile"]})
            return blocks if blocks else ""
        else:
            return "\n\n".join(
                s for s in [sections["stable"], sections["context"], sections["volatile"]] if s
            )

    def _maybe_nudge_memory(self, volatile: str) -> str:
        """Append a memory nudge to the volatile section if needed."""
        interval = agent_config.MEMORY_NUDGE_INTERVAL
        if interval <= 0 or self._turns_since_memory_use < interval:
            return volatile
        nudge = (
            "\n\n## Memory Reminder\n"
            "You haven't updated memory recently. Review the conversation "
            "for user preferences, new information, or corrections that "
            "should be persisted using the `memory` tool."
        )
        self._turns_since_memory_use = 0
        return volatile + nudge

    @staticmethod
    def _inject_memory_context(
        messages: List[Dict[str, Any]], prefetch_text: str
    ) -> List[Dict[str, Any]]:
        """Append prefetched memory context to the last user message (copy)."""
        if not prefetch_text:
            return messages
        result = [m.copy() for m in messages]
        fenced = f"\n\n<memory-context>\n{prefetch_text}\n</memory-context>"
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("role") == "user":
                content = result[i].get("content")
                if isinstance(content, list):
                    new_content = list(content)
                    new_content.append({"type": "text", "text": fenced})
                    result[i] = {**result[i], "content": new_content}
                elif isinstance(content, str):
                    result[i] = {**result[i], "content": content + fenced}
                break
        return result

    @staticmethod
    def _sanitize_output(text: str) -> str:
        """Remove internal memory-context tags from streamed output."""
        return _MEMORY_CONTEXT_TAG_RE.sub("", text)

    # ------------------------------------------------------------------
    # Tool result size management
    # ------------------------------------------------------------------

    def _manage_tool_result(
        self, name: str, result_str: str, session_id: str
    ) -> str:
        """Truncate or persist large tool results."""
        persist_threshold = agent_config.TOOL_RESULT_PERSIST_THRESHOLD
        inline_limit = agent_config.TOOL_RESULT_INLINE_LIMIT

        if len(result_str) > persist_threshold:
            path = self._persist_to_file(result_str, name, session_id)
            preview = result_str[:1000]
            return (
                f"[Output too large ({len(result_str)} chars). Saved to {path}. Preview:]\n"
                f"{preview}"
            )
        if len(result_str) > inline_limit:
            return result_str[:inline_limit] + f"\n...[truncated, {len(result_str)} total chars]"
        return result_str

    @staticmethod
    def _persist_to_file(content: str, tool_name: str, session_id: str) -> str:
        """Write large tool output to a temp file and return the path."""
        out_dir = agent_config.AGENT_DATA_DIR / "tool_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        sid = session_id[:8] if session_id else "nosess"
        filename = f"{tool_name}_{sid}_{uuid.uuid4().hex[:6]}.txt"
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    @staticmethod
    def _enforce_turn_budget(
        tool_results: List[Dict[str, Any]], budget: int
    ) -> List[Dict[str, Any]]:
        """If total chars across all results exceed budget, truncate the largest."""
        total = sum(len(tr.get("content", "")) for tr in tool_results)
        if total <= budget:
            return tool_results

        while total > budget:
            largest_idx = max(range(len(tool_results)), key=lambda i: len(tool_results[i].get("content", "")))
            old = tool_results[largest_idx]["content"]
            if len(old) <= 500:
                break
            new_len = max(500, len(old) // 2)
            tool_results[largest_idx]["content"] = old[:new_len] + f"\n...[budget-truncated from {len(old)} chars]"
            total = sum(len(tr.get("content", "")) for tr in tool_results)

        return tool_results

    # ------------------------------------------------------------------
    # Main ReAct loop
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        user_message: str,
        history: Optional[List[Dict[str, Any]]] = None,
        topic_title: str = "",
        search_context: str = "",
        session_id: str = "",
        user_id: str = "default",
        zhihu_token: str = "",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the Agent ReAct loop with streaming.

        Yields normalized events:
          {"type": "text_delta", "content": "..."}
          {"type": "thinking_delta", "content": "..."}
          {"type": "tool_call", "name": "...", "input": {...}}
          {"type": "tool_result", "name": "...", "result_preview": "..."}
          {"type": "usage_summary", ...}
          {"type": "error", "message": "..."}
        """
        self.initialize(user_id=user_id, zhihu_token=zhihu_token, session_id=session_id)

        api_key = agent_config.LLM_API_KEY
        if not api_key or not api_key.strip():
            yield {"type": "error", "message": "LLM API 密钥未配置"}
            return

        transport_mode = agent_config.get_transport_mode()
        transport = get_transport(transport_mode)
        if not transport:
            yield {"type": "error", "message": f"Transport '{transport_mode}' not available"}
            return

        # Prefetch memory context
        prefetch_text = self._memory_manager.prefetch_all(user_message, session_id=session_id)

        # Build layered system prompt
        sections = self._build_system_prompt_sections(topic_title, search_context)
        sections["volatile"] = self._maybe_nudge_memory(sections["volatile"])
        system_param = self._format_system_for_transport(sections, transport_mode)

        # Build messages
        messages = self._build_messages(user_message, history or [])
        api_messages = self._inject_memory_context(messages, prefetch_text)

        # Store user message in session DB
        if self._session_db and session_id:
            self._session_db.ensure_session(session_id, user_id=user_id)
            self._session_db.append_message(session_id, "user", user_message)

        # Context compression
        if self._compressor and self._compressor.should_compress(api_messages):
            logger.info("Compressing context...")
            api_messages = await self._compressor.compress(
                api_messages, memory_manager=self._memory_manager
            )

        # Tool definitions
        tools = self._tool_registry.get_definitions()

        # Per-session trackers
        final_text = ""
        used_memory_tool = False
        empty_retries = 0
        token_tracker = TokenUsageTracker()
        guardrails = ToolGuardrails(
            max_repeat=agent_config.TOOL_MAX_REPEAT,
            max_consecutive_errors=agent_config.TOOL_MAX_CONSECUTIVE_ERRORS,
        )

        # ---- ReAct loop ----
        for iteration in range(agent_config.AGENT_MAX_ITERATIONS):
            token_tracker.new_turn(model=agent_config.LLM_MODEL)

            kwargs = transport.build_kwargs(
                model=agent_config.LLM_MODEL,
                messages=api_messages,
                tools=tools if tools else None,
                system=system_param,
                max_tokens=4096,
                temperature=0.7,
            )

            tool_calls_in_response: List[Dict[str, Any]] = []
            text_parts: List[str] = []
            tool_blocks: Dict[int, Dict[str, Any]] = {}
            stop_reason = None

            # ---------- Stream with retry ----------
            stream_succeeded = False
            for attempt in range(agent_config.MAX_STREAM_RETRIES + 1):
                try:
                    async for event in transport.stream_api(
                        api_key=api_key,
                        base_url=agent_config.LLM_BASE_URL,
                        kwargs=kwargs,
                    ):
                        etype = event.get("type")

                        if etype == "error":
                            yield event
                            return

                        elif etype == "text_delta":
                            raw = event.get("content", "")
                            sanitized = self._sanitize_output(raw)
                            text_parts.append(raw)
                            if sanitized:
                                yield {"type": "text_delta", "content": sanitized}

                        elif etype == "thinking_delta":
                            yield event

                        elif etype == "thinking_start":
                            yield event

                        elif etype == "tool_call_start":
                            idx = event.get("index", 0)
                            tool_blocks[idx] = {
                                "id": event.get("id", str(uuid.uuid4())),
                                "name": event.get("name", ""),
                                "input_json": "",
                            }

                        elif etype == "tool_call_delta":
                            idx = event.get("index", 0)
                            tool = tool_blocks.get(idx)
                            if tool is not None:
                                tool["input_json"] += event.get("partial_json", "")

                        elif etype == "tool_call_end":
                            idx = event.get("index", 0)
                            tool = tool_blocks.pop(idx, None)
                            if tool is not None:
                                parsed_input = self._parse_tool_input(
                                    tool["name"], tool.get("input_json", "")
                                )
                                tool_calls_in_response.append({
                                    "id": tool["id"],
                                    "name": tool["name"],
                                    "input": parsed_input,
                                })
                                yield {
                                    "type": "tool_call",
                                    "name": tool["name"],
                                    "input": parsed_input,
                                }

                        elif etype == "done":
                            stop_reason = event.get("stop_reason", "stop")

                        elif etype == "usage":
                            token_tracker.record_usage(event)

                    stream_succeeded = True
                    break  # stream completed OK

                except (httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ReadError) as e:
                    if attempt < agent_config.MAX_STREAM_RETRIES:
                        logger.warning(
                            "Stream dropped (attempt %d/%d), retrying: %s",
                            attempt + 1, agent_config.MAX_STREAM_RETRIES, e,
                        )
                        tool_blocks.clear()
                        continue
                    logger.error("Stream failed after %d retries: %s", agent_config.MAX_STREAM_RETRIES, e)
                    yield {"type": "error", "message": f"AI 服务连接不稳定: {e}"}
                    return
                except Exception as e:
                    logger.error("Agent stream error: %s", e)
                    yield {"type": "error", "message": f"AI 服务异常: {e}"}
                    return

            if not stream_succeeded:
                return

            # ---------- Content filter handling ----------
            if stop_reason == "content_filter":
                accumulated_text = "".join(text_parts).strip()
                logger.warning("Content filter triggered at iteration %d", iteration)
                filter_note = (
                    "\n\n---\n*[注意：由于该话题涉及敏感内容，AI 回答在此处被截断。"
                    "建议尝试调整提问角度，从学术研究、政策解读、经济影响等客观视角切入。]*"
                )
                yield {"type": "text_delta", "content": filter_note}
                final_text = accumulated_text + filter_note
                if self._session_db and session_id and final_text:
                    self._session_db.append_message(session_id, "assistant", final_text)
                break

            # ---------- Empty response recovery ----------
            accumulated_text = "".join(text_parts).strip()
            if not tool_calls_in_response and not accumulated_text:
                if empty_retries < agent_config.MAX_EMPTY_RETRIES:
                    empty_retries += 1
                    logger.warning("Empty response (retry %d/%d)", empty_retries, agent_config.MAX_EMPTY_RETRIES)
                    api_messages.append({
                        "role": "assistant",
                        "content": [{"type": "text", "text": "(empty)"}],
                    })
                    api_messages.append({
                        "role": "user",
                        "content": [{"type": "text", "text":
                            "Your previous response was empty. Please continue with the task."}],
                    })
                    continue
                else:
                    yield {"type": "text_delta", "content": "\n\n[AI 返回了空响应，请重试]"}
                    break

            # Reset empty retry counter on successful content
            if accumulated_text or tool_calls_in_response:
                empty_retries = 0

            # ---------- No tool calls → agent finished ----------
            if not tool_calls_in_response:
                final_text = accumulated_text
                if self._session_db and session_id and final_text:
                    self._session_db.append_message(session_id, "assistant", final_text)
                break

            # Check if memory tool was used
            for tc in tool_calls_in_response:
                if tc["name"] == "memory":
                    used_memory_tool = True

            # Build assistant message with tool calls
            assistant_content: List[Dict[str, Any]] = []
            if text_parts:
                assistant_content.append({"type": "text", "text": "".join(text_parts)})
            for tc in tool_calls_in_response:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            api_messages.append({"role": "assistant", "content": assistant_content})

            # ---------- Execute tools (with guardrails + parallel) ----------
            tool_results_content: List[Dict[str, Any]] = []

            # Check if all tools are safe for parallel execution
            all_safe = (
                agent_config.PARALLEL_TOOL_ENABLED
                and len(tool_calls_in_response) > 1
                and all(tc["name"] in PARALLEL_SAFE_TOOLS for tc in tool_calls_in_response)
            )

            if all_safe:
                results = await self._execute_tools_parallel(
                    tool_calls_in_response, guardrails, session_id
                )
                for tc, (managed_result, guardrail_msg) in zip(tool_calls_in_response, results):
                    token_tracker.record_tool_call()
                    content = guardrail_msg if guardrail_msg else managed_result
                    yield {
                        "type": "tool_result",
                        "name": tc["name"],
                        "result_preview": content[:200],
                    }
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": content,
                    })
                    if self._session_db and session_id:
                        self._session_db.append_message(
                            session_id, "tool", content[:500],
                            tool_name=tc["name"], tool_call_id=tc["id"],
                        )
            else:
                for tc in tool_calls_in_response:
                    token_tracker.record_tool_call()
                    guardrail_msg = guardrails.check_before_execute(tc["name"], tc["input"])
                    if guardrail_msg:
                        logger.warning("Guardrail triggered for %s: %s", tc["name"], guardrail_msg)
                        content = guardrail_msg
                    else:
                        result_str = await self._tool_registry.dispatch(tc["name"], tc["input"])
                        managed = self._manage_tool_result(tc["name"], result_str, session_id)
                        content = managed
                        if '"success": false' in result_str.lower() or '"error"' in result_str.lower():
                            guardrails.record_error()
                        else:
                            guardrails.record_success()

                    yield {
                        "type": "tool_result",
                        "name": tc["name"],
                        "result_preview": content[:200],
                    }
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": content,
                    })
                    if self._session_db and session_id:
                        self._session_db.append_message(
                            session_id, "tool", content[:500],
                            tool_name=tc["name"], tool_call_id=tc["id"],
                        )

            # Enforce per-turn budget
            tool_results_content = self._enforce_turn_budget(
                tool_results_content, agent_config.TURN_TOTAL_BUDGET
            )

            api_messages.append({"role": "user", "content": tool_results_content})
            text_parts = []

        else:
            # ---- Graceful degradation: max iterations reached ----
            logger.warning("Max iterations (%d) reached — requesting final summary", agent_config.AGENT_MAX_ITERATIONS)
            api_messages.append({
                "role": "user",
                "content": [{"type": "text", "text":
                    "You have reached the maximum number of tool call rounds. "
                    "Please provide a final summary of what was accomplished "
                    "and any remaining work, without using any tools."}],
            })
            graceful_kwargs = transport.build_kwargs(
                model=agent_config.LLM_MODEL,
                messages=api_messages,
                tools=None,
                system=system_param,
                max_tokens=4096,
                temperature=0.7,
            )
            graceful_parts: List[str] = []
            try:
                async for event in transport.stream_api(
                    api_key=api_key,
                    base_url=agent_config.LLM_BASE_URL,
                    kwargs=graceful_kwargs,
                ):
                    etype = event.get("type")
                    if etype == "text_delta":
                        raw = event.get("content", "")
                        sanitized = self._sanitize_output(raw)
                        graceful_parts.append(raw)
                        if sanitized:
                            yield {"type": "text_delta", "content": sanitized}
                    elif etype == "usage":
                        token_tracker.record_usage(event)
            except Exception as e:
                logger.error("Graceful degradation stream error: %s", e)
                yield {"type": "text_delta", "content": "\n\n[已达到最大工具调用轮次]"}

            final_text = "".join(graceful_parts)
            if self._session_db and session_id and final_text:
                self._session_db.append_message(session_id, "assistant", final_text)

        # ---- Emit usage summary ----
        usage_summary = token_tracker.summary()
        if usage_summary.get("total_tokens", 0) > 0:
            yield {"type": "usage_summary", **usage_summary}

        # ---- Post-session actions (always run) ----
        if used_memory_tool:
            self._turns_since_memory_use = 0
        else:
            self._turns_since_memory_use += 1

        self._memory_manager.sync_all(user_message, final_text, session_id=session_id)

        if session_id:
            if agent_config.SKILL_AUTO_EXTRACT and self._skill_extractor:
                asyncio.create_task(
                    self._run_skill_extraction(session_id),
                    name=f"skill_extract_{session_id[:8]}",
                )
            if agent_config.MEMORY_AUTO_REVIEW and self._memory_reviewer and self._memory_provider:
                asyncio.create_task(
                    self._run_memory_review(session_id),
                    name=f"mem_review_{session_id[:8]}",
                )

    # ------------------------------------------------------------------
    # Tool helpers
    # ------------------------------------------------------------------

    def _parse_tool_input(self, name: str, raw_json: str) -> Any:
        """Parse, repair, and coerce tool call arguments."""
        if not raw_json or not raw_json.strip():
            return {}
        repaired = repair_tool_args(raw_json)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError:
            logger.warning("Cannot parse tool args for %s after repair: %s", name, repaired[:200])
            return {"raw": raw_json}

        if isinstance(parsed, dict):
            schema = self._tool_registry.get_tool_schema(name)
            if schema:
                parsed = coerce_tool_args(parsed, schema)
        return parsed

    async def _execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        guardrails: ToolGuardrails,
        session_id: str,
    ) -> List[tuple]:
        """Execute read-only tools concurrently. Returns (managed_result, guardrail_msg) tuples."""

        async def _run_one(tc: Dict[str, Any]) -> tuple:
            gmsg = guardrails.check_before_execute(tc["name"], tc["input"])
            if gmsg:
                return ("", gmsg)
            result_str = await self._tool_registry.dispatch(tc["name"], tc["input"])
            managed = self._manage_tool_result(tc["name"], result_str, session_id)
            if '"success": false' in result_str.lower() or '"error"' in result_str.lower():
                guardrails.record_error()
            else:
                guardrails.record_success()
            return (managed, None)

        results = await asyncio.gather(
            *[_run_one(tc) for tc in tool_calls],
            return_exceptions=True,
        )
        final = []
        for r in results:
            if isinstance(r, Exception):
                final.append((f"Tool execution error: {r}", None))
            else:
                final.append(r)
        return final

    # ------------------------------------------------------------------
    # Message building
    # ------------------------------------------------------------------

    def _build_messages(
        self, user_message: str, history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for item in history[-40:]:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append({
                "role": role,
                "content": [{"type": "text", "text": content}],
            })
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_message}],
        })
        return messages

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------

    async def _run_skill_extraction(self, session_id: str) -> None:
        """Background task: extract skills from a completed session."""
        try:
            if not self._session_db or not self._skill_extractor or not self._skill_manager:
                return

            messages = self._session_db.get_messages(session_id)
            if len(messages) < 4:
                return

            existing_names = self._skill_loader.skill_names() if self._skill_loader else []
            candidates = await self._skill_extractor.extract_from_messages(messages, existing_names)

            for candidate in candidates:
                result = await self._skill_manager.create(
                    name=candidate["name"],
                    description=candidate["description"],
                    triggers=candidate.get("triggers", []),
                    tools=candidate.get("tools", []),
                    body=candidate["body"],
                )
                if result.get("success"):
                    logger.info(
                        "Auto-extracted skill: %s (%s)",
                        result.get("name"), result.get("action"),
                    )
                else:
                    logger.debug(
                        "Skill extraction skipped for '%s': %s",
                        candidate["name"], result.get("error"),
                    )
        except Exception as e:
            logger.error("Skill extraction failed for session %s: %s", session_id[:8], e)

    async def _run_memory_review(self, session_id: str) -> None:
        """Background task: LLM-driven post-session memory review."""
        try:
            if not self._session_db or not self._memory_reviewer or not self._memory_provider:
                return

            messages = self._session_db.get_messages(session_id)
            if len(messages) < 3:
                return

            updated = await self._memory_reviewer.review_session(
                messages=messages,
                memory_store=self._memory_provider.store,
            )
            if updated:
                logger.info(
                    "Memory auto-review applied %d update(s) for session %s",
                    updated, session_id[:8],
                )
        except Exception as e:
            logger.error("Memory review failed for session %s: %s", session_id[:8], e)

    def shutdown(self):
        """Clean shutdown of all subsystems."""
        self._memory_manager.shutdown_all()
        if self._session_db:
            self._session_db.close()
        shutdown_mcp_servers()


# Global singleton
_agent_loop: Optional[AgentLoop] = None


def get_agent_loop() -> AgentLoop:
    global _agent_loop
    if _agent_loop is None:
        _agent_loop = AgentLoop()
    return _agent_loop


async def agent_chat_stream(
    user_message: str,
    history: List[Dict[str, Any]] | None = None,
    topic_title: str = "",
    search_context: str = "",
    session_id: str = "",
    user_id: str = "default",
    zhihu_token: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """Drop-in replacement for the old agent_service.agent_chat_stream."""
    loop = get_agent_loop()
    async for event in loop.chat_stream(
        user_message=user_message,
        history=history,
        topic_title=topic_title,
        search_context=search_context,
        session_id=session_id,
        user_id=user_id,
        zhihu_token=zhihu_token,
    ):
        yield event
