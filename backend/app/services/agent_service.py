"""Agent service — ReAct loop over MiniMax Anthropic-compatible API with tool calling.

Flow per turn:
  1. Build system prompt (role + skills + topic context)
  2. Send messages + tool definitions to MiniMax
  3. If model returns tool_use blocks, execute tools and loop
  4. Stream text_delta events back to caller
  5. Max 5 iterations to prevent runaway loops
"""
import json
import logging
from typing import Any, AsyncGenerator

import httpx

from app.config import settings
from app.services.zhihu_tools import TOOL_DEFINITIONS, dispatch_tool

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5

SYSTEM_PROMPT = """你是「灵感引擎」—— 一位资深的知乎创作者 AI 助手。

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

## 你的工作方式
- 主动使用工具获取信息，而不是凭空回答
- 给出有深度、有洞察的分析，而非泛泛而谈
- 提供多个创作切入角度供用户选择
- 结合知乎平台特点给出内容建议（如：知乎用户喜欢什么样的回答）
- 在用户确认前，不要直接发布内容

## 你的风格
- 专业但不刻板，有网感但不浮躁
- 善于发现话题的独特角度
- 重视论据和数据支撑
- 语言简洁有力，信息密度高

{topic_context}"""


def _build_system_prompt(topic_title: str = "", search_context: str = "") -> str:
    topic_context = ""
    if topic_title:
        topic_context += f"\n## 当前话题\n用户正在围绕「{topic_title}」进行创作探讨。请结合这个话题提供帮助。\n"
    if search_context:
        topic_context += f"\n## 参考资料\n以下是知乎站内相关讨论：\n{search_context}\n"
    return SYSTEM_PROMPT.format(
        topic_context=topic_context if topic_context else "\n用户正在进行自由创作探索。\n"
    )


def _build_anthropic_tools() -> list[dict]:
    """Convert our tool definitions to Anthropic tool format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in TOOL_DEFINITIONS
    ]


def _build_messages(user_message: str, history: list[dict]) -> list[dict]:
    """Build Anthropic-format messages from chat history."""
    messages: list[dict[str, Any]] = []
    for item in history[-20:]:
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


async def agent_chat_stream(
    user_message: str,
    history: list[dict] | None = None,
    topic_title: str = "",
    search_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the Agent ReAct loop with streaming.

    Yields normalized events:
      {"type": "text_delta", "content": "..."}
      {"type": "thinking_delta", "content": "..."}
      {"type": "tool_call", "name": "...", "input": {...}}
      {"type": "tool_result", "name": "...", "result": "..."}
      {"type": "error", "message": "..."}
    """
    api_key = settings.MINIMAX_API_KEY
    if not api_key or not api_key.strip():
        yield {"type": "error", "message": "MiniMax API 密钥未配置"}
        return

    model = settings.MINIMAX_MODEL or "MiniMax-M1"
    base_url = "https://api.minimaxi.com/anthropic"
    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    system_prompt = _build_system_prompt(topic_title, search_context)
    tools = _build_anthropic_tools()
    messages = _build_messages(user_message, history or [])

    for iteration in range(MAX_ITERATIONS):
        payload = {
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": messages,
            "tools": tools,
            "stream": True,
        }

        tool_calls_in_response: list[dict] = []
        text_parts: list[str] = []
        tool_blocks: dict[int, dict] = {}
        stop_reason = None

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error("Agent API error %s: %s", resp.status_code, body.decode(errors="ignore"))
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
                            err_msg = data.get("error", {}).get("message", "Unknown error")
                            yield {"type": "error", "message": err_msg}
                            return

                        event_type = data.get("type")

                        if event_type == "message_delta":
                            stop_reason = data.get("delta", {}).get("stop_reason")

                        elif event_type == "content_block_start":
                            index = data.get("index", -1)
                            block = data.get("content_block", {}) or {}
                            if block.get("type") == "tool_use":
                                tool_blocks[index] = {
                                    "id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "input_json": "",
                                }
                            elif block.get("type") == "thinking":
                                yield {"type": "thinking_start"}

                        elif event_type == "content_block_delta":
                            index = data.get("index", -1)
                            delta = data.get("delta", {}) or {}
                            delta_type = delta.get("type")

                            if delta_type == "text_delta" and delta.get("text"):
                                text_parts.append(delta["text"])
                                yield {"type": "text_delta", "content": delta["text"]}
                            elif delta_type == "thinking_delta" and delta.get("thinking"):
                                yield {"type": "thinking_delta", "content": delta["thinking"]}
                            elif delta_type == "input_json_delta" and delta.get("partial_json"):
                                tool = tool_blocks.get(index)
                                if tool is not None:
                                    tool["input_json"] += delta["partial_json"]

                        elif event_type == "content_block_stop":
                            index = data.get("index", -1)
                            tool = tool_blocks.pop(index, None)
                            if tool is not None:
                                parsed_input: Any = {}
                                raw = tool.get("input_json", "")
                                if raw and raw.strip():
                                    try:
                                        parsed_input = json.loads(raw)
                                    except json.JSONDecodeError:
                                        parsed_input = {"raw": raw}
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

        except httpx.TimeoutException:
            yield {"type": "error", "message": "AI 响应超时，请重试"}
            return
        except Exception as e:
            logger.error("Agent stream error: %s", e)
            yield {"type": "error", "message": f"AI 服务异常: {e}"}
            return

        if not tool_calls_in_response:
            return

        assistant_content: list[dict] = []
        if text_parts:
            assistant_content.append({"type": "text", "text": "".join(text_parts)})
        for tc in tool_calls_in_response:
            assistant_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["input"],
            })

        messages.append({"role": "assistant", "content": assistant_content})

        tool_results_content: list[dict] = []
        for tc in tool_calls_in_response:
            result_str = await dispatch_tool(tc["name"], tc["input"])

            truncated = result_str[:3000] if len(result_str) > 3000 else result_str

            yield {
                "type": "tool_result",
                "name": tc["name"],
                "result_preview": truncated[:200],
            }

            tool_results_content.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": truncated,
            })

        messages.append({"role": "user", "content": tool_results_content})
        text_parts = []

    yield {"type": "text_delta", "content": "\n\n[已达到最大工具调用轮次]"}
