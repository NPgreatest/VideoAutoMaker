#!/usr/bin/env python3
from __future__ import annotations


def openai_generate_image(
    prompt: str,
    negative_prompt: str | None,
    size: str,
) -> dict:
    """
    Placeholder for a future OpenAI image provider implementation.
    """

    return {
        "status": "not_implemented",
        "reason": "OpenAI text_image provider has not been implemented yet.",
    }


__all__ = ["openai_generate_image"]
