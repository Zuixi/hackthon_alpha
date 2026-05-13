"""Abstract base for provider transports."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.agent.transports.types import NormalizedResponse


class ProviderTransport(ABC):
    """Base class for provider-specific format conversion and normalization.

    A transport owns the data path for one api_mode:
      convert_messages -> convert_tools -> build_kwargs -> call_api / stream_api -> normalize_response
    """

    @property
    @abstractmethod
    def api_mode(self) -> str:
        ...

    @abstractmethod
    def convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        ...

    @abstractmethod
    def convert_tools(self, tools: List[Dict[str, Any]]) -> Any:
        ...

    @abstractmethod
    def build_kwargs(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **params,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def normalize_response(self, response: Any, **kwargs) -> NormalizedResponse:
        ...

    @abstractmethod
    async def stream_api(
        self,
        api_key: str,
        base_url: str,
        kwargs: Dict[str, Any],
    ) -> AsyncGenerator[dict, None]:
        """Stream raw events from the provider API.

        Yields dicts with keys like:
          {"type": "text_delta", "content": "..."}
          {"type": "thinking_delta", "content": "..."}
          {"type": "tool_call_start", "index": N, "id": "...", "name": "..."}
          {"type": "tool_call_delta", "index": N, "partial_json": "..."}
          {"type": "tool_call_end", "index": N}
          {"type": "done", "stop_reason": "..."}
          {"type": "usage", "prompt_tokens": N, "completion_tokens": N}
        """
        ...
        yield {}  # type: ignore
