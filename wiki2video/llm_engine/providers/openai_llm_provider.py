# llm_engine/providers/openai_llm_provider.py
from __future__ import annotations
import backoff
import requests

from .base_provider import BaseLLMProvider
from ...config.config_vars import BACKOFF_MAX_TRIES, BACKOFF_MAX_TIME



class OpenAILLMProvider(BaseLLMProvider):
    DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"

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
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "OpenAI support is not installed.\n"
                "Install it with:\n\n"
                "  pip install 'wiki2video[openai]'"
            )

        client = OpenAI(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        content = completion.choices[0].message.content
        return {
            "content": content,
            "raw": completion,
        }
