#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

import backoff
import requests
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest, Prosody
from pydub import AudioSegment

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.pipeline.schema import ScriptBlock
from videogen.pipeline.utils import get_character_info

# -------------------------------
# 环境变量和 Fish Audio 初始化
# -------------------------------
load_dotenv()
AUDIO_FISH_API_KEY = os.getenv("AUDIO_FISH_API_KEY")
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))

session = Session(AUDIO_FISH_API_KEY)


def _get_voice_content(block: Optional[ScriptBlock]) -> str:
    if block:
        if getattr(block, "voice", None):
            return block.voice
        if getattr(block, "text", None):
            return block.text
    return ""


# -------------------------------
# TTS 核心函数
# -------------------------------
@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter
)
def _tts_fish_request_internal(text: str, out_path: Path, model_id: str) -> bytes:
    """调用 Fish Audio TTS，返回音频字节"""
    request = TTSRequest(
        text=text,
        reference_id=model_id,
        prosody=Prosody(volume=-4.0, speed=1.2)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()
    with open(out_path, "wb") as f:
        for chunk in session.tts(request):
            f.write(chunk)
            audio_buffer.extend(chunk)
    print(f"[FishTTS] ✅ Segment audio saved to {out_path}")
    return bytes(audio_buffer)


def _split_text_into_phrases(text: str) -> List[str]:
    """根据标点拆分成短句，用于分段生成音频"""
    # 常见的中英文分隔符：句号、逗号、问号、叹号、顿号、分号
    phrases = re.split(r"(?<=[。！？!?,，、；;])", text)
    # 去掉空白和太短的片段
    return [p.strip() for p in phrases if len(p.strip()) > 0]


# -------------------------------
# 主方法：多段生成 + 合并 + 手动字幕
# -------------------------------
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
        duration_ms: Optional[int] = None,
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        try:
            # 1️⃣ 读取文本
            voice_content = _get_voice_content(block).strip()
            print(voice_content)
            if not voice_content:
                return {"ok": False, "artifacts": [], "meta": {}, "error": "No input text provided."}

            # 2️⃣ 获取角色对应的模型 ID
            model_id = None
            if block and getattr(block, "character", None):
                character_info = get_character_info(block.character)
                if character_info and "model_id" in character_info:
                    model_id = character_info["model_id"]
                    print(f"[FishTTS] Using model_id from character '{block.character}': {model_id}")
            if not model_id:
                raise ValueError("No model_id provided for TTS")

            # 3️⃣ 拆分成短句
            phrases = _split_text_into_phrases(voice_content)
            if not phrases:
                phrases = [voice_content]

            project_dir = workdir / "project" / project
            audio_dir = project_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)

            # 4️⃣ 为每个短句生成独立音频
            segments_meta = []
            combined_audio = AudioSegment.silent(duration=0)
            cursor_ms = 0

            for idx, phrase in enumerate(phrases):
                segment_path = audio_dir / f"{target_name}_seg{idx+1}.wav"
                segment_bytes = _tts_fish_request_internal(phrase, segment_path, model_id)
                if not segment_bytes:
                    continue

                # 加载音频段计算时长
                seg_audio = AudioSegment.from_file(segment_path)
                seg_duration = len(seg_audio)
                combined_audio += seg_audio

                segments_meta.append({
                    "index": idx + 1,
                    "start": cursor_ms / 1000.0,
                    "end": (cursor_ms + seg_duration) / 1000.0,
                    "text": phrase
                })
                cursor_ms += seg_duration

            # 5️⃣ 合并音频输出
            full_path = audio_dir / f"{target_name}.wav"
            combined_audio.export(full_path, format="wav")
            total_duration = len(combined_audio)

            print(f"[FishTTS] ✅ Combined audio exported: {full_path}")

            # 6️⃣ 写入 meta 信息
            meta = {
                "project": project,
                "target_name": target_name,
                "audio_path": str(full_path),
                "total_duration": total_duration,
                "segments": segments_meta  # ✅ 每个短句的手动字幕时间
            }

            return {"ok": True, "artifacts": [str(full_path)], "meta": meta, "error": None}

        except Exception as e:
            print(f"[FishTTS] ❌ Error: {e}")
            return {"ok": False, "artifacts": [], "meta": {}, "error": str(e)}
