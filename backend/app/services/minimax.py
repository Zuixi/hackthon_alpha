"""MiniMax API service with streaming support.

API docs: https://platform.minimax.io/docs/api-reference/text-post
Base URL: https://api.minimax.io
Endpoint: POST /v1/text/chatcompletion_v2
"""
import httpx
import json
import logging
from typing import AsyncGenerator
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
    BASE_URL = "https://api.minimax.io"
    ENDPOINT = "/v1/text/chatcompletion_v2"

    def __init__(self):
        self.api_key = settings.MINIMAX_API_KEY
        self.model = settings.MINIMAX_MODEL

    @property
    def _is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(
        self,
        user_message: str,
        history: list[dict],
        topic_title: str = "",
        search_context: str = "",
    ) -> list[dict]:
        topic_context = ""
        if topic_title:
            topic_context += f"当前讨论的热点：{topic_title}\n"
        if search_context:
            topic_context += f"\n以下是知乎站内相关讨论供参考：\n{search_context}"

        system_prompt = CREATIVE_ASSISTANT_PROMPT.format(
            topic_context=topic_context if topic_context else "用户正在进行自由创作探索。"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-20:])
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat_stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
        topic_title: str = "",
        search_context: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from MiniMax API via SSE."""
        if not self._is_configured:
            logger.warning("MiniMax API key not configured, returning fallback")
            yield _FALLBACK_RESPONSES[0]
            return

        messages = self._build_messages(
            user_message, history or [], topic_title, search_context
        )

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error(f"MiniMax API error {resp.status_code}: {body.decode()}")
                        yield f"AI 服务异常 (HTTP {resp.status_code})，请稍后重试。"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            # Check for API-level errors
                            base_resp = data.get("base_resp", {})
                            if base_resp.get("status_code", 0) != 0:
                                err_msg = base_resp.get("status_msg", "Unknown error")
                                logger.error(f"MiniMax API error: {err_msg}")
                                yield f"AI 服务返回错误：{err_msg}"
                                return

                            choices = data.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            logger.error("MiniMax API timeout")
            yield "\n\n[AI 响应超时，请重新发送消息]"
        except httpx.ConnectError as e:
            logger.error(f"MiniMax API connection error: {e}")
            yield "\n\n[无法连接 AI 服务，请检查网络]"
        except Exception as e:
            logger.error(f"MiniMax streaming error: {e}")
            yield f"\n\n[AI 服务异常: {e}]"

    async def chat_completion(
        self,
        user_message: str,
        history: list[dict] | None = None,
        topic_title: str = "",
        search_context: str = "",
    ) -> str:
        """Non-streaming chat completion (fallback)."""
        if not self._is_configured:
            return _FALLBACK_RESPONSES[0]

        messages = self._build_messages(
            user_message, history or [], topic_title, search_context
        )

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()

                base_resp = data.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
                    raise Exception(base_resp.get("status_msg", "Unknown error"))

                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                raise Exception(f"MiniMax API returned no choices: {data}")
        except Exception as e:
            logger.error(f"MiniMax completion error: {e}")
            raise


minimax_service = MiniMaxService()
