#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import backoff
import requests

from wiki2video.config.config_manager import config
from wiki2video.config.config_vars import (
    BACKOFF_MAX_TRIES,
    BACKOFF_MAX_TIME,
)

# 初始化 Google Cloud Text-to-Speech 客户端
# 注意：需要设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量或使用默认凭据


# -------------------------------
# TTS 主函数（Google Cloud）
# -------------------------------
@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter,
)
def google_tts(text: str, out_path: Path) -> bytes:
    """
    使用 Google Cloud Text-to-Speech API 生成语音并返回音频字节。

    Args:
        text: 要转换为语音的文本
        out_path: 输出音频文件路径

    Returns:
        音频的原始字节数据

    Raises:
        ValueError: 如果配置缺失
        RuntimeError: 如果生成过程中出现错误
    """
    try:
        from google.cloud import texttospeech
    except ImportError:
        raise RuntimeError(
            "Google support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[google]'"
        )

    client = texttospeech.TextToSpeechClient()
    project_id = config.get("google", "project_id")
    if not project_id:
        raise ValueError("Missing google.project_id in config.json")

    # 确保输出目录存在
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 从配置获取参数，如果没有则使用默认值
    language_code = config.get("google", "tts_language_code") or "en-US"
    voice_name = config.get("google", "tts_voice_name")  # 可选，如果指定则使用特定声音
    ssml_gender = config.get("google", "tts_gender") or "NEUTRAL"  # MALE, FEMALE, NEUTRAL
    speaking_rate = config.get("google", "tts_speed") or 1.0
    audio_encoding = config.get("google", "tts_audio_encoding") or "MP3"  # MP3, LINEAR16, etc.

    try:
        # 设置输入文本
        synthesis_input = texttospeech.SynthesisInput(text=text)
        # 设置声音参数
        if voice_name:
            # 如果指定了具体的声音名称，使用它
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )
        else:
            # 否则根据语言和性别选择声音
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=getattr(texttospeech.SsmlVoiceGender, ssml_gender.upper()),
            )

        # 设置音频配置
        audio_config = texttospeech.AudioConfig(
            audio_encoding=getattr(texttospeech.AudioEncoding, audio_encoding.upper()),
            speaking_rate=speaking_rate,
        )

        # 调用 API 生成语音
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_bytes = response.audio_content

        if not audio_bytes:
            raise RuntimeError("Google TTS returned empty audio content")

        # 写入文件
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        print(f"[Google TTS] ✅ Segment audio saved to {out_path}")
        return audio_bytes

    except Exception as e:
        raise RuntimeError(f"Google TTS generation failed: {e}") from e


__all__ = ["google_tts"]

