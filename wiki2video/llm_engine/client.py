from __future__ import annotations
from typing import List, Optional

from .types import ChatMessage, ChatResult
from .errors import LLMConfigError
from .api_router import get_llm_provider_config
from .settings import (
    get_llm_backoff_base,
    get_llm_backoff_max_time,
    get_llm_backoff_max_tries,
    get_llm_timeout_seconds,
)


class LLMEngine:
    """
    项目统一的 LLM 客户端封装：
    - chat(messages) 低层
    - ask_text(prompt) 简单问答
    - ask_decision(prompt, keywords) 关键词判定
    - gen_react_jsx(prompt, width, height) 生成 React 组件 JSX
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        provider_cfg = get_llm_provider_config()

        resolved_api_url = api_url or provider_cfg["api_url"]
        resolved_api_key = api_key or provider_cfg["api_key"]
        resolved_default_model = default_model or provider_cfg["default_model"]

        if not resolved_api_key:
            raise LLMConfigError(
                f"Missing API key for LLM platform '{provider_cfg['name']}'. "
                "Set the corresponding api_keys entry or pass api_key explicitly."
            )

        self.default_model = resolved_default_model
        provider_cls = provider_cfg["provider_cls"]
        self.provider_name = provider_cfg["name"]

        self.provider = provider_cls(
            api_url=resolved_api_url,
            api_key=resolved_api_key,
            timeout_seconds=get_llm_timeout_seconds(),
            max_retries=get_llm_backoff_max_tries(),
            backoff_base=get_llm_backoff_base(),
            backoff_max_time=get_llm_backoff_max_time(),
        )

    # -------- 基础接口 --------
    def chat(self, messages: List[ChatMessage], *, model: Optional[str] = None, **kw) -> ChatResult:
        return self.provider.chat(messages=messages, model=model or self.default_model, **kw)

    # -------- 便捷封装 --------
    def ask_text(self, prompt: str, **kw) -> str:
        res = self.chat([{"role": "user", "content": prompt}], **kw)
        return res["content"].strip()

    def ask_decision(self, prompt: str, positive_keywords=("generate",), fallback="search", **kw) -> str:
        """
        返回 positive 或 fallback：等价你原来的 ask_llm_decision()
        """
        text = self.ask_text(prompt, **kw).lower()
        return next((k for k in positive_keywords if k in text), fallback)


# -------- 全局单例（简单好用） --------
_engine_singleton: Optional[LLMEngine] = None


def get_engine() -> LLMEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = LLMEngine()
    return _engine_singleton
