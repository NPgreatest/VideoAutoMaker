from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
import requests

from ..types import ChatMessage, ChatResult
from ..errors import LLMHTTPError
from openai import OpenAI
client = OpenAI()


class OpenAICompatProvider:
    """
    兼容 /v1/chat/completions 的提供方（如 SiliconFlow/OpenAI 兼容网关）
    """
    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        timeout_seconds: int,
        max_retries: int,
        backoff_base: float,
        backoff_max_time: Optional[int] = None,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max_time = backoff_max_time

    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        stream: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        is_openai = (
                "openai.com" in self.api_url
                or "api.openai.com" in self.api_url
        )
        if is_openai:
            response = client.responses.create(
                model=model,
                input=messages,
            )

            # OpenAI 新版 API
            payload["max_completion_tokens"] = max_tokens
            payload["temperature"] = 1
        else:
            # 兼容老式 /v1/chat/completions
            payload["max_tokens"] = max_tokens
            payload["temperature"] = temperature


        if extra:
            payload.update(extra)

        backoff = self.backoff_base
        start = time.perf_counter()
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                print(f"chat attempt {attempt}/{self.max_retries}")
            try:
                resp = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if resp.status_code >= 400:
                    raise LLMHTTPError(resp.status_code, resp.text)
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return {"content": content, "raw": data}
            except Exception as e:
                print(f"chat failed due to {e}")
                elapsed = time.perf_counter() - start
                if attempt >= self.max_retries:
                    raise
                if self.backoff_max_time is not None and elapsed >= self.backoff_max_time:
                    raise
                sleep_time = backoff
                if self.backoff_max_time is not None:
                    remaining = max(self.backoff_max_time - elapsed, 0.0)
                    sleep_time = min(sleep_time, remaining)
                time.sleep(sleep_time)
                backoff *= 2.0  # 简单指数回退
