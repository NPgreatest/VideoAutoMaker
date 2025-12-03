# llm_engine/providers/silicon_llm_provider.py

from __future__ import annotations
from __future__ import annotations

import backoff
import requests

from .base_provider import BaseLLMProvider
from ...config.config_vars import BACKOFF_MAX_TRIES, BACKOFF_MAX_TIME



class SiliconLLMProvider(BaseLLMProvider):
    DEFAULT_API_URL = "https://api.siliconflow.cn/v1/chat/completions"

    def __init__(self, api_url=None, **kwargs):
        super().__init__(
            api_url=api_url or self.DEFAULT_API_URL,
            **kwargs,
        )

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.HTTPError),
        max_tries=BACKOFF_MAX_TRIES,
        max_time=BACKOFF_MAX_TIME,
        jitter=backoff.random_jitter
    )
    def chat(
        self,
        messages,
        model,
        temperature=0.2,
        max_tokens=1200,
        stream=False,
        extra=None,
    ):
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if extra:
            payload.update(extra)

        resp = requests.post(
            self.api_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_seconds,
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {
            "content": content,
            "raw": data,
        }
