#!/usr/bin/env python3
from __future__ import annotations

import base64
from wiki2video.config.config_manager import config

REQUEST_TIMEOUT = 300


def openai_generate_image(
    prompt: str,
    negative_prompt: str | None,
    size: str,
) -> bytes:

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[openai]'"
        )

    token = config.get("openai", "api_key")
    if not token:
        raise ValueError("Missing OpenAI API key in config.json (openai.api_key).")

    model = config.get("openai", "text_image_model") or "gpt-image-1"
    image_size = size or "1024x1024"

    client = OpenAI(api_key=token, timeout=REQUEST_TIMEOUT)

    try:
        result = client.images.generate(
            model=model,
            prompt=prompt,
            size=image_size,
        )
    except Exception as e:
        raise ValueError(f"OpenAI image generation failed: {e}") from e

    if not result.data or not result.data[0].b64_json:
        raise ValueError("OpenAI response did not include base64 image data.")

    try:
        return base64.b64decode(result.data[0].b64_json)
    except Exception as e:
        raise ValueError("Failed to decode OpenAI image base64 data.") from e


__all__ = ["openai_generate_image"]
