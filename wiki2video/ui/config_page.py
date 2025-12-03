#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr

from wiki2video.config.config_manager import SUPPORTED_PLATFORMS, config


def _load_config_values():
    cfg = config.to_dict()
    platforms = cfg.get("platforms", {})
    api_keys = cfg.get("api_keys", {})
    global_cfg = cfg.get("global_config", {})
    return [
        platforms.get("llm"),
        platforms.get("tts"),
        platforms.get("text_to_video"),
        platforms.get("image"),
        api_keys.get("openai_api_key"),
        api_keys.get("deepseek_api_key"),
        api_keys.get("siliconflow_api_key"),
        api_keys.get("runway_api_key"),
        api_keys.get("fal_api_key"),
        api_keys.get("replicate_api_key"),
        api_keys.get("gpt_sovits_api_key"),
        api_keys.get("coqui_tts_api_key"),
        api_keys.get("text_audio_api_key"),
        api_keys.get("google_api_key"),
        api_keys.get("google_cx_key"),
        cfg.get("llm_default_model"),
        cfg.get("backoff_max_tries"),
        cfg.get("backoff_max_time"),
        global_cfg.get("font_path"),
        global_cfg.get("bgm_path"),
        global_cfg.get("tts_server_ip"),
        global_cfg.get("tts_port"),
    ]


def _save_config_values(
    llm_platform,
    tts_platform,
    text_to_video_platform,
    image_platform,
    openai_key,
    deepseek_key,
    silicon_key,
    runway_key,
    fal_key,
    replicate_key,
    gpt_sovits_key,
    coqui_key,
    text_audio_key,
    google_key,
    google_cx_key,
    llm_default_model,
    backoff_max_tries,
    backoff_max_time,
    font_path,
    bgm_path,
    tts_ip,
    tts_port,
):
    try:
        config.set("platforms", "llm", value=llm_platform or None)
        config.set("platforms", "tts", value=tts_platform or None)
        config.set("platforms", "text_to_video", value=text_to_video_platform or None)
        config.set("platforms", "image", value=image_platform or None)

        config.set("api_keys", "openai_api_key", value=openai_key or None)
        config.set("api_keys", "deepseek_api_key", value=deepseek_key or None)
        config.set("api_keys", "siliconflow_api_key", value=silicon_key or None)
        config.set("api_keys", "runway_api_key", value=runway_key or None)
        config.set("api_keys", "fal_api_key", value=fal_key or None)
        config.set("api_keys", "replicate_api_key", value=replicate_key or None)
        config.set("api_keys", "gpt_sovits_api_key", value=gpt_sovits_key or None)
        config.set("api_keys", "coqui_tts_api_key", value=coqui_key or None)
        config.set("api_keys", "text_audio_api_key", value=text_audio_key or None)
        config.set("api_keys", "google_api_key", value=google_key or None)
        config.set("api_keys", "google_cx_key", value=google_cx_key or None)

        config.set("llm_default_model", value=llm_default_model or None)
        config.set("backoff_max_tries", value=backoff_max_tries)
        config.set("backoff_max_time", value=backoff_max_time)

        config.set("global_config", "font_path", value=font_path or None)
        config.set("global_config", "bgm_path", value=bgm_path or None)
        config.set("global_config", "tts_server_ip", value=tts_ip or None)
        config.set("global_config", "tts_port", value=tts_port or None)

        return "✅ 配置已保存到 ~/.config/wiki2video/config.json"
    except Exception as exc:  # pragma: no cover - UI path
        return f"❌ 保存失败: {exc}"


def build_config_page() -> None:
    with gr.Column():
        gr.Markdown(
            "### ⚙️ Configuration\n"
            "选择平台、填入 API Key，并调整运行时参数。所有设置写入 `~/.config/wiki2video/config.json`。"
        )

        with gr.Row():
            llm_platform = gr.Dropdown(
                label="LLM Platform",
                choices=SUPPORTED_PLATFORMS["llm"],
                allow_custom_value=False,
            )
            tts_platform = gr.Dropdown(
                label="TTS Platform",
                choices=SUPPORTED_PLATFORMS["tts"],
                allow_custom_value=False,
            )

        with gr.Row():
            text_to_video_platform = gr.Dropdown(
                label="Text-to-Video Platform",
                choices=SUPPORTED_PLATFORMS["text_to_video"],
                allow_custom_value=False,
            )
            image_platform = gr.Dropdown(
                label="Image Platform",
                choices=SUPPORTED_PLATFORMS["image"],
                allow_custom_value=False,
            )

        with gr.Accordion("API Keys", open=True):
            openai_key = gr.Textbox(label="OpenAI API Key", type="password")
            deepseek_key = gr.Textbox(label="DeepSeek API Key", type="password")
            silicon_key = gr.Textbox(label="SiliconFlow API Key", type="password")
            runway_key = gr.Textbox(label="Runway API Key", type="password")
            fal_key = gr.Textbox(label="FAL API Key", type="password")
            replicate_key = gr.Textbox(label="Replicate API Key", type="password")
            gpt_sovits_key = gr.Textbox(label="GPT-SoVITS API Key", type="password")
            coqui_key = gr.Textbox(label="Coqui TTS API Key", type="password")
            text_audio_key = gr.Textbox(label="TextAudio API Key", type="password")
            google_key = gr.Textbox(label="Google API Key", type="password")
            google_cx_key = gr.Textbox(label="Google CX Key", type="password")

        with gr.Row():
            llm_default_model = gr.Textbox(label="LLM Default Model", placeholder="e.g. gpt-4.1")
            backoff_max_tries = gr.Number(label="BACKOFF_MAX_TRIES", precision=0)
            backoff_max_time = gr.Number(label="BACKOFF_MAX_TIME (seconds)", precision=0)

        with gr.Accordion("Global settings", open=False):
            font_path = gr.Textbox(label="Font Path", placeholder="assets/microhei.ttc")
            bgm_path = gr.Textbox(label="Default BGM Path (optional)")
            tts_ip = gr.Textbox(label="TTS Server IP", placeholder="127.0.0.1")
            tts_port = gr.Textbox(label="TTS Server Port", placeholder="9880")

        with gr.Row():
            load_btn = gr.Button("Load Config")
            save_btn = gr.Button("Save Config", variant="primary")
        status = gr.Markdown("")

    load_btn.click(
        fn=_load_config_values,
        outputs=[
            llm_platform,
            tts_platform,
            text_to_video_platform,
            image_platform,
            openai_key,
            deepseek_key,
            silicon_key,
            runway_key,
            fal_key,
            replicate_key,
            gpt_sovits_key,
            coqui_key,
            text_audio_key,
            google_key,
            google_cx_key,
            llm_default_model,
            backoff_max_tries,
            backoff_max_time,
            font_path,
            bgm_path,
            tts_ip,
            tts_port,
        ],
    )
    save_btn.click(
        fn=_save_config_values,
        inputs=[
            llm_platform,
            tts_platform,
            text_to_video_platform,
            image_platform,
            openai_key,
            deepseek_key,
            silicon_key,
            runway_key,
            fal_key,
            replicate_key,
            gpt_sovits_key,
            coqui_key,
            text_audio_key,
            google_key,
            google_cx_key,
            llm_default_model,
            backoff_max_tries,
            backoff_max_time,
            font_path,
            bgm_path,
            tts_ip,
            tts_port,
        ],
        outputs=status,
    )
