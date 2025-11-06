#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional

import backoff
import requests
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest, Prosody

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.pipeline.schema import ScriptBlock

load_dotenv()
AUDIO_FISH_API_KEY = os.getenv("AUDIO_FISH_API_KEY")
AUDIO_FISH_MODEL_ID = os.getenv("AUDIO_FISH_MODEL_ID")
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))


session = Session(AUDIO_FISH_API_KEY)



def _get_voice_content(block: Optional[ScriptBlock], text: str = "") -> str:
    """优先从 block 中取 voice/text，其次用 text 或 prompt"""
    if block:
        if getattr(block, "voice", None):
            return block.voice
        if getattr(block, "text", None):
            return block.text
    return text


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter
)
def _tts_fish_request_internal(text: str, out_path: Path) -> None:

    request = TTSRequest(
        text=text,
        reference_id=AUDIO_FISH_MODEL_ID,
        prosody=Prosody(volume=-4.0, speed=1.2)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "wb") as f:
        for chunk in session.tts(request):
            f.write(chunk)

    print(f"[FishTTS] ✅ Audio saved to {out_path}")


def _tts_fish_request(text: str, out_path: Path) -> bool:
    try:
        _tts_fish_request_internal(text, out_path)
        return True
    except requests.exceptions.RequestException as e:
        print(f"[FishTTS] ❌ Request failed after retries: {e}")
        return False
    except Exception as e:
        print(f"[FishTTS] ❌ Unexpected error after retries: {e}")
        return False


@register_method
class FishAudioMethod(BaseMethod):

    NAME = "fish_audio"
    OUTPUT_KIND = "audio"

    def run(
        self,
        *,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        try:
            # 1️⃣ 获取文本内容
            voice_content = _get_voice_content(block, text).strip()
            if not voice_content:
                return {"ok": False, "artifacts": [], "meta": {}, "error": "No input text provided."}


            project_dir = workdir / "project" / project
            wav_path = project_dir / "audio" / f"{target_name}.wav"
            ok = _tts_fish_request(voice_content, wav_path)

            if not ok:
                return {"ok": False, "artifacts": [], "meta": {}, "error": "TTS generation failed."}

            # 计算音频时长
            try:
                from pydub.utils import mediainfo
                info = mediainfo(str(wav_path))
                total_duration = float(info.get('duration', 0)) * 1000  # 转换为毫秒
            except Exception as e:
                print(f"[SiliconTTS] Warning: Could not get audio duration: {e}")
                total_duration = 0

            # ✅ 成功返回
            meta = {
                "project": project,
                "target_name": target_name,
                "audio_path": str(wav_path),
                "total_duration": total_duration,
            }
            return {"ok": True, "artifacts": [str(wav_path)], "meta": meta, "error": None}

        except Exception as e:
            return {"ok": False, "artifacts": [], "meta": {}, "error": str(e)}
