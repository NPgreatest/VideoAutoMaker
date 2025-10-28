from __future__ import annotations
import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import requests
from dotenv import load_dotenv
from pydub.utils import mediainfo

from .utils import get_total_audio_duration_ms
from ..base import BaseMethod
from ..registry import register_method
from ...pipeline.schema import ScriptBlock

# ----------------- 环境 & 常量 -----------------
load_dotenv()

TTS_SERVER_IP = os.getenv("TTS_SERVER_IP", "127.0.0.1")
TTS_PORT = os.getenv("TTS_PORT", "9880")
TTS_URL = f"http://{TTS_SERVER_IP}:{TTS_PORT}/tts"

# 默认参数（每次请求会 copy 一份再覆盖）
DEFAULT_TTS_PARAMS = {
    "text_lang": "zh",
    "cut_punc": "。，？",
    "speed": "1.4",
    "ref_audio_path": "output/reference.wav",
    "prompt_text": "就是跟他这个成长的外部环境有关系，和本身的素质也有关系，他是一个",
    "prompt_lang": "zh",
    "text_split_method": "cut5",
    "batch_size": 1,
    "media_type": "wav",
    "streaming_mode": "true",
    "speed_factor" : 1.2,
}

# ----------------- 工具函数 -----------------
def _load_audio_config(workdir: Path) -> Dict[str, Any]:
    """
    从 {workdir}/config/audio_config.yaml 读取配置；没有则返回空 dict。
    配置建议结构：
      characters:
        default:
          lang: "en"
          ref_audio_path: "output/reference.wav"
          prompt_text: "参考音色文本"
        alice:
          lang: "en"
          ref_audio_path: "assets/alice.wav"
          prompt_text: "hello I'm Alice"
    """
    cfg_path = workdir / "config" / "audio_config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # 延迟导入，避免无依赖时崩
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _switch_character_model(cfg: Dict[str, Any], character: str, emotion: str) -> Dict[str, Any]:
    """
    返回对 TTS 参数的定制覆盖（lang/ref_audio_path/prompt_text 等）。
    emotion 目前保留参数位，若配置里有基于 emotion 的细化可自行扩展。
    """
    out: Dict[str, Any] = {}
    char_cfg = (cfg.get("characters") or {}).get(character) or (cfg.get("characters") or {}).get("default") or {}
    # 语言
    if "lang" in char_cfg:
        out["text_lang"] = char_cfg["lang"]
        out["prompt_lang"] = char_cfg["lang"]
    # 参考音频
    if "ref_audio_path" in char_cfg:
        out["ref_audio_path"] = char_cfg["ref_audio_path"]
    elif "default_ref_audio_path" in cfg:
        out["ref_audio_path"] = cfg["default_ref_audio_path"]
    # 参考文本
    if "prompt_text" in char_cfg:
        out["prompt_text"] = char_cfg["prompt_text"]
    elif "default_prompt_text" in cfg:
        out["prompt_text"] = cfg["default_prompt_text"]
    # 情绪占位（如需可加入 pitch/speed/emotion tag 等）
    if (cfg.get("emotions") or {}).get(emotion):
        out.update(cfg["emotions"][emotion])  # 例如 {"speed":"1.2"} 之类
    return out

def _get_voice_content(block: Optional[ScriptBlock]) -> str:
    """
    从 block 中获取 voice 内容，如果没有 voice 则使用 text 内容。
    返回用于 TTS 的文本内容。
    """
    if not block:
        return ""
    
    # 优先使用 voice 字段
    voice_content = block.voice
    if voice_content:
        return voice_content
    
    # 如果没有 voice，则使用 text 字段
    text_content = block.text
    return text_content

def _format_time(seconds: float) -> str:
    mins, secs = divmod(seconds, 60.0)
    hours, mins = divmod(int(mins), 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{int(hours):02}:{int(mins):02}:{int(secs)%60:02},{ms:03}"


def _has_ffmpeg() -> bool:
    from shutil import which
    return which("ffmpeg") is not None

import subprocess, shlex
from pathlib import Path
from typing import List

def _concat_wavs_with_ffmpeg(wav_paths: List[Path], out_path: Path) -> bool:
    if not wav_paths:
        print("[concat] no wav files")
        return False
    # absolute, safely-quoted paths
    lst = out_path.with_suffix(".txt")
    lines = [f"file {shlex.quote(str(p.resolve()))}" for p in wav_paths]
    lst.write_text("\n".join(lines), encoding="utf-8")

    # first try lossless copy
    cmd = [
        "ffmpeg","-y",
        "-f","concat","-safe","0",
        "-i",str(lst),
        "-c","copy",
        str(out_path)
    ]
    print(f"[concat] {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print(f"[concat] success (copy) -> {out_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[concat] copy mode failed ({e.returncode}), retrying with re-encode…")

        # fallback: force uniform pcm_s16le
        cmd = [
            "ffmpeg","-y",
            "-f","concat","-safe","0",
            "-i",str(lst),
            "-ar","44100","-ac","2",
            "-c:a","pcm_s16le",
            str(out_path)
        ]
        print(f"[concat] {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"[concat] success (re-encoded) -> {out_path}")
            return True
        else:
            print("[concat] re-encode failed")
            print("---- STDOUT ----")
            print(proc.stdout)
            print("---- STDERR ----")
            print(proc.stderr)
            print("----------------")
            return False
    finally:
        try:
            lst.unlink()
        except Exception:
            pass


def _tts_request(params: Dict[str, Any], out_path: Path) -> bool:
    try:
        # 你的服务是 GET 带 query 的形式；考虑兼容 POST：
        resp = requests.get(TTS_URL, params=params, timeout=60)
        if resp.status_code == 200:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
            return True
        else:
            print(f"[TTS] HTTP {resp.status_code} {resp.reason}")
            return False
    except Exception as e:
        print(f"[TTS] Request error: {e}")
        return False

def _gen_block_audio(
    block: Dict[str, Any],
    project_dir: Path,
    base_name: str,
    cfg: Dict[str, Any],
    *,
    character: str = "default",
    emotion: str = "neutral",
    regen: bool = True,
) -> Tuple[List[Path], str, int]:
    """
    为单个 block 生成音频，返回：
      - wav 文件路径列表（单个文件）
      - srt 文本
      - 总时长（毫秒）
    """
    # 获取 voice 内容，如果没有则使用 text
    voice_content = _get_voice_content(block)
    if not voice_content:
        return [], "", 0
    
    audio_dir = project_dir / "audio"
    subs_dir = project_dir / "subtitles"
    audio_dir.mkdir(parents=True, exist_ok=True)
    subs_dir.mkdir(parents=True, exist_ok=True)

    overrides = _switch_character_model(cfg, character, emotion)

    # 生成单个音频文件
    wav_name = f"{base_name}.wav"
    wav_path = audio_dir / wav_name

    if wav_path.exists() and not regen:
        pass
    else:
        params = {**DEFAULT_TTS_PARAMS, **overrides}
        params["text"] = voice_content
        ok = _tts_request(params, wav_path)
        if not ok:
            print(f"[TTS] Failed for block {base_name}, inserting 0s placeholder.")
            wav_path.touch()

    # duration in ms
    dur_ms = get_total_audio_duration_ms(wav_path)
    
    # 生成 SRT 内容
    srt_lines = [
        f"1\n{_format_time(0)} --> {_format_time(dur_ms / 1000)}\n{voice_content}\n\n"
    ]
    srt_text = "".join(srt_lines)
    
    return [wav_path], srt_text, dur_ms


@register_method
class AudioEngineMethod(BaseMethod):
    """
    NAME: 'audio_engine'
    - 输入：block（包含 voice 或 text 字段）、prompt（可选）、text（脚本文本；若空则用 prompt）
    - 输出：
        单个 wav：{workdir}/project/{project}/audio/{target_name}.wav
        字幕 srt：{workdir}/project/{project}/subtitles/{target_name}.srt
    meta:
        {"total_duration": float, "clips": [<rel paths>], "merged": <rel path>}
    """
    NAME = "audio_engine"
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
        block: Optional[ScriptBlock] = None
    ) -> Dict[str, Any]:
        try:
            # 优先使用 block 中的 voice/text 内容
            if block:
                voice_content = _get_voice_content(block)
                if not voice_content:
                    return {
                        "ok": False,
                        "artifacts": [],
                        "meta": {},
                        "error": "No voice or text content found in block.",
                    }
            else:
                # 回退到原有的 text/prompt 逻辑
                voice_content = (text or prompt or "").strip()
                if not voice_content:
                    return {
                        "ok": False,
                        "artifacts": [],
                        "meta": {},
                        "error": "No input text to synthesize (both 'text' and 'prompt' are empty).",
                    }

            project_dir = workdir / "project" / project
            project_dir.mkdir(parents=True, exist_ok=True)

            # 加载配置（如果存在）
            cfg = _load_audio_config(workdir)

            # 生成音频 + srt
            clips, srt_text, total_sec = _gen_block_audio(
                block=block,
                project_dir=project_dir,
                base_name=target_name,
                cfg=cfg,
                character=cfg.get("default_character", "default"),
                emotion=cfg.get("default_emotion", "neutral"),
                regen=True,   # 如需跳过已存在可改为 False
            )

            if not clips:
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": "Failed to generate audio clips.",
                }

            # 写入 srt
            subs_dir = project_dir / "subtitles"
            srt_path = subs_dir / f"{target_name}.srt"
            srt_path.write_text(srt_text, encoding="utf-8")

            # 对于单个文件，merged 就是原文件
            merged_path = clips[0]  # 只有一个文件
            merged_rel = str(merged_path.relative_to(project_dir))

            # 工件 & meta
            artifacts: List[str] = [str(srt_path)]
            artifacts.extend([str(p) for p in clips])

            meta = {
                "project": project,
                "target_name": target_name,
                "total_duration": total_sec,
                "clips": [str(p.relative_to(project_dir)) for p in clips],
                "srt": str(srt_path.relative_to(project_dir)),
                "merged": merged_rel,
                "tts_url": TTS_URL,
            }

            return {"ok": True, "artifacts": artifacts, "meta": meta, "error": None}

        except Exception as e:
            return {"ok": False, "artifacts": [], "meta": {}, "error": str(e)}


# def switch_character_model(character: str, emotion: str):
#     character = "dingzhen"
#     char_cfg = AUDIO_CONFIG.get("characters", {}).get(character)
#     if not char_cfg:
#         print(f"⚠️ No config found for character: {character}")
#         return
#
#     try:
#         if "gpt_weights" in char_cfg:
#             requests.get(f"http://{TTS_SERVER_IP}:{TTS_PORT}/set_gpt_weights", params={"weights_path": char_cfg["gpt_weights"]})
#         if "sovits_weights" in char_cfg:
#             requests.get(f"http://{TTS_SERVER_IP}:{TTS_PORT}/set_sovits_weights", params={"weights_path": char_cfg["sovits_weights"]})
#         print(f"✅ Switched models for {character}")
#     except Exception as e:
#         print(f"❌ Error switching models: {e}")
#
#     # Update global TTS params
#     emotion_cfg = char_cfg.get("emotions", {}).get(emotion)
#     if not emotion_cfg:
#         print(f"⚠️ No emotion config for {character} - {emotion}, using default")
#         emotion_cfg = char_cfg.get("emotions", {}).get("default")
#
#     DEFAULT_TTS_PARAMS["ref_audio_path"] = emotion_cfg.get("ref_audio_path", DEFAULT_TTS_PARAMS["ref_audio_path"])
#     DEFAULT_TTS_PARAMS["prompt_text"] = emotion_cfg.get("prompt_text", DEFAULT_TTS_PARAMS["prompt_text"])
#     return char_cfg.get("language", {})