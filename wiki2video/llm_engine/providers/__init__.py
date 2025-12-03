from .openai_llm_provider import OpenAILLMProvider
from .silicon_llm_provider import SiliconLLMProvider

PROVIDER_REGISTRY = {
    "openai": OpenAILLMProvider,
    "siliconflow": SiliconLLMProvider,
}

__all__ = ["PROVIDER_REGISTRY"]
