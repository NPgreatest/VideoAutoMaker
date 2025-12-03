# llm_engine/providers/base_provider.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from ..types import ChatMessage, ChatResult

class BaseLLMProvider(ABC):

    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        timeout_seconds: int,
        max_retries: int,
        backoff_base: float,
        backoff_max_time: Optional[int],
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max_time = backoff_max_time

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        **kwargs,
    ) -> ChatResult:
        ...
