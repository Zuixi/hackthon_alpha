"""MiniMax Anthropic-compatible API service (Agent-friendly).

Reference:
- https://platform.minimaxi.com/docs/api-reference/text-anthropic-api
- Base URL: https://api.minimaxi.com/anthropic
- Endpoint: POST /v1/messages
"""
import json
import logging
from typing import Any, AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CREATIVE_ASSISTANT_PROMPT = """你是一位专业的知乎创作助手，帮助创作者基于热点话题进行高质量内容创作。

{topic_context}

你的能力：
1. 深度分析热点事件的背景、核心争议点和社会影响
2. 提供多个独特的切入角度供创作者选择
3. 帮助梳理论点、论据和行文逻辑
4. 给出适合知乎平台的内容结构建议
5. 结合知乎站内已有讨论，提供有深度的见解

请用专业、有洞察力且富有知乎风格的方式回答。注重逻辑严谨性和信息密度。"""

_FALLBACK_RESPONSES = [
    "MiniMax API 密钥未配置，无法调用 AI 服务。请在 .env 中设置 MINIMAX_API_KEY。",
    "您可以先浏览热点话题，配置好 API 密钥后再开始 AI 对话。",
]


class MiniMaxService:
    BASE_URL = "https://api.minimaxi.com/anthropic"
    ENDPOINT = "/v1/messages"
    DEFAULT_MODEL = "MiniMax-M2.7"

    def __init__(self):
        self.api_key = settings.MINIMAX_API_KEY
        self.model = settings.MINIMAX_MODEL or self.DEFAULT_MODEL

    @property
    def _is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _build_system_prompt(self, topic_title: str = "", search_context: str = "") -> str:
        topic_context = ""
        if topic_title:
            topic_context += f"当前讨论的热点：{topic_title}\n"
        if search_context:
            topic_context += f"\n以下是知乎站内相关讨论供参考：\n{search_context}"
        return CREATIVE_ASSISTANT_PROMPT.format(
            topic_context=topic_context if topic_context else "用户正在进行自由创作探索。"
        )

    def _build_messages(
        self,
        user_message: str,
        history: list[dict],
    ) -> list[dict]:
        """Build Anthropic-format messages.

        Input history format (existing code):
        [{"role": "user|assistant", "content": "..."}]
        """
        messages: list[dict[str, Any]] = []
        for item in history[-20:]:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append(
                {
                    "role": role,
                    "content": [{"type": "text", "text": content}],
                }
            )

        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": user_message}],
            }
        )
        return messages

    @staticmethod
    def _extract_text_from_message(data: dict) -> str:
        parts: list[str] = []
        for block in data.get("content", []):
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
        return "".join(parts)

    async def chat_stream_blocks(
        self,
        user_message: str,
        history: list[dict] | None = None,
        topic_title: str = "",
        search_context: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream full Anthropic blocks (thinking/text/tool_use) via normalized events."""
        if not self._is_configured:
            logger.warning("MiniMax API key not configured, returning fallback error event")
            yield {"type": "error", "message": _FALLBACK_RESPONSES[0]}
            return

        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0.7,
            "system": self._build_system_prompt(topic_title, search_context),
            "messages": self._build_messages(user_message, history or []),
            "stream": True,
        }
        url = f"{self.BASE_URL}{self.ENDPOINT}"
        tool_blocks: dict[int, dict[str, Any]] = {}

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error(
                            "MiniMax API stream error %s: %s",
                            resp.status_code,
                            body.decode(errors="ignore"),
                        )
                        yield {
                            "type": "error",
                            "message": f"AI 服务异常 (HTTP {resp.status_code})，请稍后重试。",
                        }
                        return

                    async for line in resp.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if data.get("type") == "error":
                            err = data.get("error", {})
                            msg = err.get("message") or "Unknown error"
                            logger.error("MiniMax stream returned error event: %s", msg)
                            yield {"type": "error", "message": f"AI 服务返回错误：{msg}"}
                            return

                        event_type = data.get("type")
                        if event_type == "content_block_start":
                            index = data.get("index", -1)
                            block = data.get("content_block", {}) or {}
                            block_type = block.get("type")
                            if block_type == "tool_use":
                                tool_blocks[index] = {
                                    "id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "input_json": "",
                                }
                                yield {
                                    "type": "tool_use_start",
                                    "id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                }
                            elif block_type == "thinking":
                                yield {"type": "thinking_start"}
                            elif block_type == "text":
                                yield {"type": "text_start"}

                        elif event_type == "content_block_delta":
                            index = data.get("index", -1)
                            delta = data.get("delta", {}) or {}
                            delta_type = delta.get("type")
                            if delta_type == "text_delta" and delta.get("text"):
                                yield {"type": "text_delta", "content": delta["text"]}
                            elif delta_type == "thinking_delta" and delta.get("thinking"):
                                yield {"type": "thinking_delta", "content": delta["thinking"]}
                            elif delta_type == "input_json_delta" and delta.get("partial_json"):
                                tool = tool_blocks.get(index)
                                if tool is not None:
                                    piece = delta["partial_json"]
                                    tool["input_json"] += piece
                                    yield {
                                        "type": "tool_use_delta",
                                        "id": tool.get("id", ""),
                                        "content": piece,
                                    }

                        elif event_type == "content_block_stop":
                            index = data.get("index", -1)
                            tool = tool_blocks.pop(index, None)
                            if tool is not None:
                                raw_input = tool.get("input_json", "")
                                parsed_input: Any = raw_input
                                if raw_input and raw_input.strip():
                                    try:
                                        parsed_input = json.loads(raw_input)
                                    except json.JSONDecodeError:
                                        parsed_input = raw_input
                                yield {
                                    "type": "tool_use",
                                    "id": tool.get("id", ""),
                                    "name": tool.get("name", ""),
                                    "input": parsed_input,
                                }
        except httpx.TimeoutException:
            logger.error("MiniMax API timeout")
            yield {"type": "error", "message": "\n\n[AI 响应超时，请重新发送消息]"}
        except httpx.ConnectError as e:
            logger.error("MiniMax API connection error: %s", e)
            yield {"type": "error", "message": "\n\n[无法连接 AI 服务，请检查网络]"}
        except Exception as e:
            logger.error("MiniMax streaming error: %s", e)
            yield {"type": "error", "message": f"\n\n[AI 服务异常: {e}]"}

    async def chat_stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
        topic_title: str = "",
        search_context: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from MiniMax Anthropic-compatible API via SSE."""
        if not self._is_configured:
            logger.warning("MiniMax API key not configured, returning fallback")
            yield _FALLBACK_RESPONSES[0]
            return

        async for event in self.chat_stream_blocks(
            user_message=user_message,
            history=history,
            topic_title=topic_title,
            search_context=search_context,
        ):
            if event.get("type") == "text_delta" and event.get("content"):
                yield str(event["content"])
            elif event.get("type") == "error" and event.get("message"):
                yield str(event["message"])
                return

    async def chat_completion(
        self,
        user_message: str,
        history: list[dict] | None = None,
        topic_title: str = "",
        search_context: str = "",
    ) -> str:
        """Non-streaming completion via Anthropic-compatible endpoint."""
        if not self._is_configured:
            return _FALLBACK_RESPONSES[0]

        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0.7,
            "system": self._build_system_prompt(topic_title, search_context),
            "messages": self._build_messages(user_message, history or []),
        }
        url = f"{self.BASE_URL}{self.ENDPOINT}"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {resp.text[:500]}"
                    )
                data = resp.json()
                text = self._extract_text_from_message(data)
                if text:
                    return text
                raise RuntimeError(f"MiniMax API returned no text content: {data}")
        except Exception as e:
            logger.error("MiniMax completion error: %s", e)
            raise


minimax_service = MiniMaxService()
