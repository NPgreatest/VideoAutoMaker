from __future__ import annotations
from typing import List, Dict, Any, Optional

from .types import ChatMessage, ChatResult
from .errors import LLMConfigError
from .settings import (
    LLM_API_URL, LLM_API_KEY, LLM_DEFAULT_MODEL,
)
from .providers import OpenAICompatProvider

class LLMEngine:
    """
    项目统一的 LLM 客户端封装：
    - chat(messages) 低层
    - ask_text(prompt) 简单问答
    - ask_decision(prompt, keywords) 关键词判定
    - gen_react_jsx(prompt, width, height) 生成 React 组件 JSX
    """
    def __init__(self, api_url: str = LLM_API_URL, api_key: Optional[str] = LLM_API_KEY, default_model: str = LLM_DEFAULT_MODEL):
        if not api_key:
            raise LLMConfigError("Missing LLM_API_KEY / SILICONFLOW_API_TOKEN")
        self.default_model = default_model
        self.provider = OpenAICompatProvider(api_url=api_url, api_key=api_key)

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
