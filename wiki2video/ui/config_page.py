#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr

from wiki2video.config.config_manager import SUPPORTED_PLATFORMS, config


def _load_config_values():
    cfg = config.to_dict()
    platforms = cfg.get("platforms", {})
    global_cfg = cfg.get("global_config", {})
    
    # Get platform-specific configs
    llm_platform = platforms.get("llm")
    llm_default_model = config.get(llm_platform, "default_model") if llm_platform else None
    
    return [
        platforms.get("llm"),
        platforms.get("tts"),
        platforms.get("text_to_video"),
        platforms.get("image"),
        config.get("openai", "api_key"),
        config.get("deepseek", "api_key"),
        config.get("siliconflow", "api_key"),
        config.get("runway", "api_key"),
        config.get("fal", "api_key"),
        config.get("replicate", "api_key"),
        config.get("gpt_sovits", "api_key"),
        config.get("coqui", "api_key"),
        config.get("text_audio", "api_key"),
        config.get("google", "api_key"),
        config.get("google", "cx_key"),
        llm_default_model,
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

        # Save platform-specific API keys
        config.set("openai", "api_key", value=openai_key or None)
        config.set("deepseek", "api_key", value=deepseek_key or None)
        config.set("siliconflow", "api_key", value=silicon_key or None)
        config.set("runway", "api_key", value=runway_key or None)
        config.set("fal", "api_key", value=fal_key or None)
        config.set("replicate", "api_key", value=replicate_key or None)
        config.set("gpt_sovits", "api_key", value=gpt_sovits_key or None)
        config.set("coqui", "api_key", value=coqui_key or None)
        config.set("text_audio", "api_key", value=text_audio_key or None)
        config.set("google", "api_key", value=google_key or None)
        config.set("google", "cx_key", value=google_cx_key or None)

        # Save LLM default model to the selected LLM platform
        if llm_platform and llm_default_model:
            config.set(llm_platform, "default_model", value=llm_default_model)
        
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
                choices=SUPPORTED_PLATFORMS["text_image"],
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
            llm_default_model = gr.Textbox(
                label="LLM Default Model (for selected LLM platform)", 
                placeholder="e.g. gpt-4.1 or deepseek-ai/DeepSeek-V3.1-Terminus"
            )
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
