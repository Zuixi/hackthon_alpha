"""MiniMax Anthropic-compatible transport.

MiniMax exposes an Anthropic Messages-compatible endpoint at
https://api.minimaxi.com/anthropic/v1/messages with streaming support.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.agent.transports import register_transport
from app.agent.transports.base import ProviderTransport
from app.agent.transports.types import (
    NormalizedResponse,
    ToolCall,
    Usage,
    build_tool_call,
)

logger = logging.getLogger(__name__)

_FINISH_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
    "max_tokens": "length",
}


class MiniMaxTransport(ProviderTransport):

    @property
    def api_mode(self) -> str:
        return "minimax_anthropic"

    def convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        return messages

    def convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in tools
        ]

    def build_kwargs(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **params,
    ) -> Dict[str, Any]:
        system = params.pop("system", "")
        # Support system as string or list of text blocks (for cache_control)
        if isinstance(system, list):
            system_value = system
        else:
            system_value = system
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": params.get("max_tokens", 4096),
            "temperature": params.get("temperature", 0.7),
            "system": system_value,
            "messages": self.convert_messages(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = self.convert_tools(tools)
        return kwargs

    def normalize_response(self, response: Any, **kwargs) -> NormalizedResponse:
        raise NotImplementedError("Use stream_api for MiniMax")

    async def stream_api(
        self,
        api_key: str,
        base_url: str,
        kwargs: Dict[str, Any],
    ) -> AsyncGenerator[dict, None]:
        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=kwargs) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error("MiniMax API error %s: %s", resp.status_code, body.decode(errors="ignore"))
                    yield {"type": "error", "message": f"AI 服务异常 (HTTP {resp.status_code})"}
                    return

                async for line in resp.aiter_lines():
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if data.get("type") == "error":
                        yield {"type": "error", "message": data.get("error", {}).get("message", "Unknown")}
                        return

                    event_type = data.get("type")

                    if event_type == "message_start":
                        usage = data.get("message", {}).get("usage", {})
                        if usage:
                            yield {
                                "type": "usage",
                                "prompt_tokens": usage.get("input_tokens", 0),
                                "completion_tokens": 0,
                            }

                    elif event_type == "message_delta":
                        stop_reason = data.get("delta", {}).get("stop_reason")
                        usage = data.get("usage", {})
                        if stop_reason:
                            yield {
                                "type": "done",
                                "stop_reason": _FINISH_REASON_MAP.get(stop_reason, "stop"),
                                "completion_tokens": usage.get("output_tokens", 0),
                            }

                    elif event_type == "content_block_start":
                        index = data.get("index", 0)
                        block = data.get("content_block", {}) or {}
                        if block.get("type") == "tool_use":
                            yield {
                                "type": "tool_call_start",
                                "index": index,
                                "id": block.get("id", ""),
                                "name": block.get("name", ""),
                            }
                        elif block.get("type") == "thinking":
                            yield {"type": "thinking_start"}

                    elif event_type == "content_block_delta":
                        index = data.get("index", 0)
                        delta = data.get("delta", {}) or {}
                        delta_type = delta.get("type")

                        if delta_type == "text_delta" and delta.get("text"):
                            yield {"type": "text_delta", "content": delta["text"]}
                        elif delta_type == "thinking_delta" and delta.get("thinking"):
                            yield {"type": "thinking_delta", "content": delta["thinking"]}
                        elif delta_type == "input_json_delta" and delta.get("partial_json"):
                            yield {
                                "type": "tool_call_delta",
                                "index": index,
                                "partial_json": delta["partial_json"],
                            }

                    elif event_type == "content_block_stop":
                        index = data.get("index", 0)
                        yield {"type": "tool_call_end", "index": index}


register_transport("minimax_anthropic", MiniMaxTransport)
