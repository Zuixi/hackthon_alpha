"""OpenAI Chat Completions transport.

Handles the standard OpenAI-compatible API format used by many providers
(OpenAI, DeepSeek, Qwen, Ollama, etc.).
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
    "stop": "stop",
    "tool_calls": "tool_calls",
    "length": "length",
    "content_filter": "stop",
}


class ChatCompletionsTransport(ProviderTransport):

    @property
    def api_mode(self) -> str:
        return "chat_completions"

    def convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        return messages

    def convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("input_schema", t.get("parameters", {})),
                },
            }
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
        converted = self.convert_messages(messages)
        if system:
            if isinstance(system, list):
                system_text = "\n\n".join(
                    b.get("text", "") for b in system if isinstance(b, dict) and b.get("text")
                )
            else:
                system_text = system
            if system_text:
                converted = [{"role": "system", "content": system_text}] + converted

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": converted,
            "max_tokens": params.get("max_tokens", 4096),
            "temperature": params.get("temperature", 0.7),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = self.convert_tools(tools)
        return kwargs

    def normalize_response(self, response: Any, **kwargs) -> NormalizedResponse:
        raise NotImplementedError("Use stream_api for ChatCompletions")

    async def stream_api(
        self,
        api_key: str,
        base_url: str,
        kwargs: Dict[str, Any],
    ) -> AsyncGenerator[dict, None]:
        url = f"{base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        open_tool_indices: Dict[int, bool] = {}

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=kwargs) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error("Chat API error %s: %s", resp.status_code, body.decode(errors="ignore"))
                    yield {"type": "error", "message": f"AI 服务异常 (HTTP {resp.status_code})"}
                    return

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        for idx in sorted(open_tool_indices):
                            yield {"type": "tool_call_end", "index": idx}
                        open_tool_indices.clear()
                        yield {"type": "done", "stop_reason": "stop"}
                        return

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    if not choices:
                        usage = data.get("usage")
                        if usage:
                            yield {
                                "type": "usage",
                                "prompt_tokens": usage.get("prompt_tokens", 0),
                                "completion_tokens": usage.get("completion_tokens", 0),
                            }
                        continue

                    choice = choices[0]
                    delta = choice.get("delta", {})
                    finish = choice.get("finish_reason")

                    content = delta.get("content")
                    if content:
                        yield {"type": "text_delta", "content": content}

                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        yield {"type": "thinking_delta", "content": reasoning}

                    tool_calls = delta.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            idx = tc.get("index", 0)
                            fn = tc.get("function", {})
                            if tc.get("id"):
                                if idx in open_tool_indices:
                                    yield {"type": "tool_call_end", "index": idx}
                                open_tool_indices[idx] = True
                                yield {
                                    "type": "tool_call_start",
                                    "index": idx,
                                    "id": tc["id"],
                                    "name": fn.get("name", ""),
                                }
                            if fn.get("arguments"):
                                yield {
                                    "type": "tool_call_delta",
                                    "index": idx,
                                    "partial_json": fn["arguments"],
                                }

                    if finish:
                        for idx in sorted(open_tool_indices):
                            yield {"type": "tool_call_end", "index": idx}
                        open_tool_indices.clear()
                        yield {"type": "done", "stop_reason": _FINISH_REASON_MAP.get(finish, "stop")}


register_transport("chat_completions", ChatCompletionsTransport)
