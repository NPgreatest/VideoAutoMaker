# llm_engine/router.py
from __future__ import annotations

from wiki2video.config.config_manager import config
from .errors import LLMConfigError
from .providers import PROVIDER_REGISTRY


def get_llm_provider_config():
    platform = config.get("platforms","llm")
    if platform not in PROVIDER_REGISTRY:
        raise LLMConfigError(f"Unsupported LLM platform: {platform}")

    api_key = config.get(platform, "api_key")
    model = config.get(platform, "llm_model")

    provider_cls = PROVIDER_REGISTRY[platform]

    return {
        "name": platform,
        "provider_cls": provider_cls,
        "api_key": api_key,
        "default_model": model,
    }
