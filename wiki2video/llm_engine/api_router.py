from __future__ import annotations

from typing import Optional, Type, TypedDict

from wiki2video.config.config_manager import config

from .errors import LLMConfigError
from .providers import OpenAICompatProvider


class _ProviderDefinition(TypedDict):
    provider_cls: Type[OpenAICompatProvider]
    default_api_url: str
    default_model: str


class LLMProviderConfig(TypedDict):
    name: str
    provider_cls: Type[OpenAICompatProvider]
    api_url: str
    api_key: Optional[str]
    default_model: str


_PROVIDER_REGISTRY: dict[str, _ProviderDefinition] = {
    "siliconflow": {
        "provider_cls": OpenAICompatProvider,
        "default_api_url": "https://api.siliconflow.cn/v1/chat/completions",
        "default_model": "deepseek-ai/DeepSeek-V3.1-Terminus",
    },
    "openai": {
        "provider_cls": OpenAICompatProvider,
        "default_api_url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-5-nano",
    },
}


def _normalize_platform(value: Optional[str]) -> str:
    platform = (value or "").strip().lower()
    if not platform:
        raise LLMConfigError("Missing LLM platform in config.json: set platforms.llm")
    return platform


def get_llm_provider_config() -> LLMProviderConfig:
    """
    Resolve the concrete provider implementation + defaults based on config.
    """
    platform = _normalize_platform(config.get("platforms", "llm"))

    definition = _PROVIDER_REGISTRY.get(platform)
    if not definition:
        raise LLMConfigError(f"Unsupported LLM platform '{platform}'.")

    override_api_url = config.get("global_config", "llm_api_url")
    override_model = config.get("llm_default_model")

    return {
        "name": platform,
        "provider_cls": definition["provider_cls"],
        "api_url": override_api_url or definition["default_api_url"],
        "api_key": config.get_api_key(platform),
        "default_model": override_model or definition["default_model"],
    }


__all__ = ["get_llm_provider_config", "LLMProviderConfig"]
