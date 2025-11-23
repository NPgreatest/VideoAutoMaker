#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr

from videogen.core.config_manager import ConfigManager

CONFIG_FIELDS = [
    "SILICONFLOW_API_TOKEN",
    "LLM_DEFAULT_MODEL",
    "AUDIO_FISH_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_CX_KEY",
    "TIKTOK_FORMAT_PICTURE_WIDTH_RATIO",
    "TIKTOK_FORMAT_PICTURE_X_RATIO",
    "TIKTOK_FORMAT_PICTURE_Y_RATIO",
    "TIKTOK_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO",
    "LANDSCAPE_FORMAT_PICTURE_WIDTH_RATIO",
    "LANDSCAPE_FORMAT_PICTURE_X_RATIO",
    "LANDSCAPE_FORMAT_PICTURE_Y_RATIO",
    "LANDSCAPE_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO",
    "FONT_PATH",
]


def _load_config_values():
    return [ConfigManager.get(key, "") for key in CONFIG_FIELDS]


def _save_config_values(*values):
    for key, value in zip(CONFIG_FIELDS, values):
        ConfigManager.set(key, value)
    return "✅ 配置已保存，并写回 .env。"


def build_config_page() -> None:
    inputs = []
    with gr.Column():
        gr.Markdown("### ⚙️ Config Manager\n加载、修改并保存环境配置，立即生效。")
        for key in CONFIG_FIELDS:
            is_secret = "TOKEN" in key or "API_KEY" in key
            lines = 1
            if "SCRIPT" in key or "FONT_PATH" in key:
                lines = 2
            textbox = gr.Textbox(
                label=key,
                lines=lines,
                type="password" if is_secret else "text",
            )
            inputs.append(textbox)

        with gr.Row():
            load_btn = gr.Button("Load Config")
            save_btn = gr.Button("Save Config", variant="primary")
        status = gr.Markdown("")

    load_btn.click(fn=_load_config_values, outputs=inputs)
    save_btn.click(fn=_save_config_values, inputs=inputs, outputs=status)


