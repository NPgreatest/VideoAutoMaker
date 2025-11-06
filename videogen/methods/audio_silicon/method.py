#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional

import requests
import backoff
from dotenv import load_dotenv

from videogen.methods.audio_silicon.config import ensure_voice_uri, get_default_character, list_cached_voices
from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.pipeline.schema import ScriptBlock

load_dotenv()
SILICON_API_KEY = os.getenv("SILICONFLOW_API_TOKEN")
SILICON_TTS_URL = "https://api.siliconflow.cn/v1/audio/speech"

# Backoff retry configuration from .env
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))

# =============== 默认参数 ===============
DEFAULT_SILICON_PARAMS = {
    "model": "FunAudioLLM/CosyVoice2-0.5B",
    "response_format": "wav",
    "sample_rate": 44100,
    "speed": 1.0,
    "gain": 0.0,
}


def _get_voice_content(block: Optional[ScriptBlock], text: str = "", prompt: str = "") -> str:
    """优先从 block 中取 voice/text，其次用 text 或 prompt"""
    if block:
        if getattr(block, "voice", None):
            return block.voice
        if getattr(block, "text", None):
            return block.text
    return text or prompt or ""


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter
)
def _tts_silicon_request_internal(text: str, out_path: Path, params: Dict[str, Any]) -> None:
    """Internal function that makes the actual TTS request with retry logic."""
    headers = {
        "Authorization": f"Bearer {SILICON_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(SILICON_TTS_URL, headers=headers, json=params, timeout=120)
    
    # Check HTTP status code
    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            f'HTTP {resp.status_code}: {resp.text[:200]}'
        )
    
    # Save the audio file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    print(f"[SiliconTTS] ✅ Audio saved to {out_path}")


def _tts_silicon_request(text: str, out_path: Path, params: Dict[str, Any]) -> bool:
    """调用 SiliconFlow TTS API 并保存音频，带重试逻辑"""
    try:
        _tts_silicon_request_internal(text, out_path, params)
        return True
    except requests.exceptions.RequestException as e:
        print(f"[SiliconTTS] ❌ Request failed after retries: {e}")
        return False
    except Exception as e:
        print(f"[SiliconTTS] ❌ Unexpected error after retries: {e}")
        return False


@register_method
class SiliconAudioMethod(BaseMethod):
    """
    NAME: 'silicon_audio'
    从 block.character 自动选择角色，如无则默认第一个。
    输出单个 wav 文件，不生成字幕。
    """

    NAME = "silicon_audio"
    OUTPUT_KIND = "audio"

    def run(
        self,
        *,
        prompt: str,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        try:
            # 1️⃣ 获取文本内容
            voice_content = _get_voice_content(block, text, prompt).strip()
            if not voice_content:
                return {"ok": False, "artifacts": [], "meta": {}, "error": "No input text provided."}

            # 2️⃣ 获取角色（从 block 或默认）
            character = getattr(block, "character", None)
            cached = list_cached_voices()
            if not character or character not in cached:
                character = get_default_character()
                print(f"[SiliconTTS] Using default character: {character}")

            voice_uri = ensure_voice_uri(character)

            # 4️⃣ 构造 payload
            params = {**DEFAULT_SILICON_PARAMS, "input": voice_content}
            if voice_uri:
                params["voice"] = voice_uri

            # 5️⃣ 生成音频
            project_dir = workdir / "project" / project
            wav_path = project_dir / "audio" / f"{target_name}.wav"
            ok = _tts_silicon_request(voice_content, wav_path, params)

            if not ok:
                return {"ok": False, "artifacts": [], "meta": {}, "error": "TTS generation failed."}

            # 计算音频时长
            try:
                from pydub.utils import mediainfo
                info = mediainfo(str(wav_path))
                total_duration = float(info.get('duration', 0)) * 1000  # 转换为毫秒
            except Exception as e:
                print(f"[FishTTS] Warning: Could not get audio duration: {e}")
                total_duration = 0

            # ✅ 成功返回
            meta = {
                "project": project,
                "target_name": target_name,
                "character": character,
                "voice_uri": voice_uri,
                "audio_path": str(wav_path),
                "total_duration": total_duration,
            }
            return {"ok": True, "artifacts": [str(wav_path)], "meta": meta, "error": None}

        except Exception as e:
            return {"ok": False, "artifacts": [], "meta": {}, "error": str(e)}
