#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from wiki2video.config.config_manager import config

# 导入各 provider 的核心函数
from wiki2video.methods.text_audio.providers.fish_audio_provider import fish_tts
from wiki2video.methods.text_audio.providers.openai_audio_provider import openai_tts
from wiki2video.methods.text_audio.providers.google_audio_provider import google_tts


# -------------------------------
# TTS 路由器
# -------------------------------
def tts_router(text: str, out_path: Path) -> bytes:
    platform = config.get("platforms", "tts")
    if not platform:
        raise Exception("Missing TTS platform in config.json: platforms.tts")

    platform = platform.lower().strip()
    if platform == "fish_audio":
        return fish_tts(text, out_path)

    if platform == "openai":
        return openai_tts(text, out_path)

    if platform == "google":
        return google_tts(text, out_path)

    # if platform == "siliconflow":
    #     return siliconflow_tts(...)

    raise Exception(f"TTS platform '{platform}' not supported yet.")
