from .openai_llm_provider import OpenAILLMProvider
from .silicon_llm_provider import SiliconLLMProvider
from .google_llm_provider import GoogleLLMProvider

PROVIDER_REGISTRY = {
    "openai": OpenAILLMProvider,
    "siliconflow": SiliconLLMProvider,
    "google": GoogleLLMProvider,
}

__all__ = ["PROVIDER_REGISTRY"]
