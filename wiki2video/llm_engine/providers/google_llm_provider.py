# llm_engine/providers/google_llm_provider.py
from __future__ import annotations

import backoff
import requests
from typing import List, Dict, Optional

from .base_provider import BaseLLMProvider
from ...config.config_vars import BACKOFF_MAX_TRIES, BACKOFF_MAX_TIME
from ...config.config_manager import config


class GoogleLLMProvider(BaseLLMProvider):
    """
    Google Gemini (Vertex AI) provider.

    IMPORTANT DESIGN:
    - Accept OpenAI-style messages from upper layer
    - Internally FLATTEN them into ONE prompt string
    - Call models.generate_content(contents=str)
    - This is the ONLY path that guarantees response.text
    """

    DEFAULT_API_URL = ""

    def __init__(self, api_url=None, **kwargs):
        super().__init__(
            api_url=api_url or self.DEFAULT_API_URL,
            **kwargs,
        )

        try:
            from google import genai
        except ImportError:
            raise RuntimeError(
                "Google support is not installed.\n"
                "Install it with:\n\n"
                "  pip install 'wiki2video[google]'"
            )

        project_id = config.get("google", "project_id")
        if not project_id:
            raise ValueError("Missing google.project_id in config.json")

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
        )

    # ------------------------------------------------------------
    # Message flattening (KEY PART)
    # ------------------------------------------------------------

    def _flatten_messages(self, messages: List[Dict]) -> str:
        """
        Convert OpenAI-style messages into ONE plain-text prompt.

        Order preserved:
        - system
        - user
        - assistant

        No roles, no parts — just text.
        """
        chunks: List[str] = []

        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue
            chunks.append(content.strip())

        return "\n\n".join(chunks)

    # ------------------------------------------------------------
    # Chat API
    # ------------------------------------------------------------

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.HTTPError),
        max_tries=BACKOFF_MAX_TRIES,
        max_time=BACKOFF_MAX_TIME,
        jitter=backoff.random_jitter,
    )
    def chat(
        self,
        messages,
        model,
        temperature: float = 0.2,
        max_tokens: int = 60000,
        stream: bool = False,
        extra: Optional[dict] = None,
    ):
        if stream:
            raise NotImplementedError(
                "Streaming is not supported for Google Gemini yet."
            )

        prompt = self._flatten_messages(messages)

        if not prompt:
            raise ValueError("Empty prompt after flattening messages.")

        try:
            from google.genai.types import GenerateContentConfig
        except ImportError:
            raise RuntimeError(
                "Google support is not installed.\n"
                "Install it with:\n\n"
                "  pip install 'wiki2video[google]'"
            )

        generation_config = GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,

        )
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=generation_config,

            )
            # print(f"response.text: {response.text}")
            text = response.text

            if not text:
                raise RuntimeError("Gemini returned empty text output.")

            return {
                "content": text,
                "raw": response,
            }

        except Exception as e:
            raise RuntimeError(f"Google Gemini generation failed: {e}") from e
