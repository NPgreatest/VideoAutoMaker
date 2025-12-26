#!/usr/bin/env python3
from __future__ import annotations

import base64
from typing import Optional

import requests

from wiki2video.config.config_manager import config

API_URL = "https://api.siliconflow.cn/v1/images/generations"
REQUEST_TIMEOUT = 60


def siliconflow_generate_image(
    prompt: str,
    negative_prompt: str | None,
    size: str,
) -> bytes:
    """
    Call SiliconFlow's image generation endpoint and return the raw image bytes.
    """

    token = config.get("siliconflow", "api_key")
    if not token:
        raise ValueError(
            "Missing SiliconFlow API key in config.json (siliconflow.api_key)."
        )

    payload = {
        "model": config.get("siliconflow", "text_image_model"),
        "prompt": prompt,
        "image_size": size or "1024x1024",
        "batch_size": 1,
        "seed": 4_999_999_999,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "cfg": 10.05,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("SiliconFlow returned invalid JSON content.") from exc

    image_bytes = _extract_image_bytes(data)
    if not image_bytes:
        raise ValueError("SiliconFlow response did not include image bytes.")

    return image_bytes


def _extract_image_bytes(payload: dict) -> Optional[bytes]:
    """
    Support multiple possible SiliconFlow response shapes (base64 or downloadable URL).
    """

    if not isinstance(payload, dict):
        return None

    data_entries = payload.get("data")
    if isinstance(data_entries, list):
        for entry in data_entries:
            decoded = _decode_entry(entry)
            if decoded:
                return decoded

    results = payload.get("results")
    if isinstance(results, list):
        for entry in results:
            decoded = _decode_entry(entry)
            if decoded:
                return decoded

    for key in ("image_base64", "b64_json", "base64"):
        value = payload.get(key)
        if isinstance(value, str):
            decoded = _decode_base64(value)
            if decoded:
                return decoded

    url = payload.get("url")
    if isinstance(url, str):
        return _download_url(url)

    return None


def _decode_entry(entry: object) -> Optional[bytes]:
    if not isinstance(entry, dict):
        return None

    for key in ("b64_json", "image_base64", "base64", "data"):
        data = entry.get(key)
        if isinstance(data, str):
            decoded = _decode_base64(data)
            if decoded:
                return decoded

    url = entry.get("url")
    if isinstance(url, str):
        return _download_url(url)

    return None


def _decode_base64(value: str) -> Optional[bytes]:
    try:
        return base64.b64decode(value)
    except Exception:
        return None


def _download_url(url: str) -> Optional[bytes]:
    if not url:
        return None

    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content


__all__ = ["siliconflow_generate_image"]
