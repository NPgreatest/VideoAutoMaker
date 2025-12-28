# llm_engine/client.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from .types import ChatMessage, ChatResult
from .errors import LLMConfigError
from .router import get_llm_provider_config
from .settings import (
    get_llm_backoff_base,
    get_llm_backoff_max_time,
    get_llm_backoff_max_tries,
    get_llm_timeout_seconds,
)
from jinja2 import Template
# 🔥 引入模板加载器（你项目已有）
from wiki2video.llm_engine.markdown_loader import MarkdownPromptLoader
from wiki2video.config.config_manager import config


class LLMEngine:
    """
    项目统一的 LLM 客户端封装：

    支持两类输入：
    1) chat(messages) —— 原始 LLM 消息
    2) chat_with_template(template_path_or_key, variables) —— 模板 + 替换

    并提供 ask_text() / ask_template() 等便捷封装。
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        ):
        provider_cfg = get_llm_provider_config()

        resolved_api_key = api_key or provider_cfg["api_key"]
        resolved_default_model = default_model or provider_cfg["default_model"]

        # Special handling for Google platform which uses project_id instead of api_key
        if provider_cfg["name"] == "google":
            project_id = config.get("google", "project_id")
            if not project_id:
                raise LLMConfigError(
                    f"Missing project_id for LLM platform 'google'. "
                    f"Set google.project_id in config.json."
                )
        elif not resolved_api_key:
            raise LLMConfigError(
                f"Missing API key for LLM platform '{provider_cfg['name']}'. "
                f"Set {provider_cfg['name']}.api_key in config.json or pass api_key explicitly."
            )

        self.default_model = resolved_default_model
        provider_cls = provider_cfg["provider_cls"]
        self.provider_name = provider_cfg["name"]
        self.provider = provider_cls(
            api_url=api_url,
            api_key=resolved_api_key,
            timeout_seconds=get_llm_timeout_seconds(),
            max_retries=get_llm_backoff_max_tries(),
            backoff_base=get_llm_backoff_base(),
            backoff_max_time=get_llm_backoff_max_time(),
        )

        self.prompt_loader = MarkdownPromptLoader()

    # -------------------------------------------------------------------------
    # 📌 1. 原始基础 LLM 接口
    # -------------------------------------------------------------------------
    def chat(self, messages: List[ChatMessage], *, model: Optional[str] = None, **kw) -> ChatResult:
        """低层统一聊天接口，所有 provider 都必须实现 provider.chat。"""
        model_name = model or self.default_model
        if not model_name:
            raise LLMConfigError("No default LLM model configured.")
        return self.provider.chat(messages=messages, model=model_name, **kw)


    def chat_with_template(
            self,
            template_ref: str,
            variables: Dict[str, Any],
            *,
            model: Optional[str] = None,
            **kw,
    ) -> ChatResult:

        if "." not in template_ref:
            raise ValueError("Registry 模板引用必须是 'category.key'")
        category, key = template_ref.split(".", 1)
        template = self.prompt_loader.load_from_registry(category, key)

        # ✔ Jinja2 渲染 —— 不会误解析 JSON 或 Markdown
        final_prompt = Template(template).render(**variables)

        return self.chat(
            messages=[{"role": "user", "content": final_prompt}],
            model=model or self.default_model,
            **kw,
        )

    def ask_text(self, prompt: str, **kw) -> str:
        res = self.chat([{"role": "user", "content": prompt}], **kw)
        return res["content"].strip()

    def ask_template(
        self,
        template_ref: str,
        variables: Dict[str, Any],
        *,
        model: Optional[str] = None,
        **kw,
    ) -> str:
        res = self.chat_with_template(
            template_ref=template_ref,
            variables=variables,
            model=model,
            **kw,
        )
        return res["content"].strip()


# 全局单例
_engine_singleton: Optional[LLMEngine] = None


def get_engine() -> LLMEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = LLMEngine()
    return _engine_singleton
