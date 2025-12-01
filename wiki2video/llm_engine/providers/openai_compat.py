from __future__ import annotations
import time, json
from typing import List, Dict, Any, Optional
import requests

from ..types import ChatMessage, ChatResult
from ..errors import LLMHTTPError
from ..settings import (
    LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES, LLM_BACKOFF_BASE,
)

class OpenAICompatProvider:
    """
    兼容 /v1/chat/completions 的提供方（如 SiliconFlow/OpenAI 兼容网关）
    """
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if extra:
            payload.update(extra)

        backoff = LLM_BACKOFF_BASE
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            if attempt > 1:
                print(f'chat attempt {attempt}/{LLM_MAX_RETRIES}')
            try:
                resp = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                if resp.status_code >= 400:
                    raise LLMHTTPError(resp.status_code, resp.text)
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return {"content": content, "raw": data}
            except Exception as e:
                print(f'chat failed due to {e}')
                if attempt >= LLM_MAX_RETRIES:
                    raise
                time.sleep(backoff)
                backoff *= 2.0  # 简单指数回退
