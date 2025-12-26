#!/usr/bin/env python3
"""Environment checks for wiki2video."""

from __future__ import annotations

import subprocess
from typing import List, Tuple

import typer
from wiki2video.config.config_manager import config

app = typer.Typer(
    help="Verify local dependencies and API keys.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _run_version(cmd: List[str]) -> Tuple[str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        line = (proc.stdout or proc.stderr or "").splitlines()[0]
        return "ok", line.strip()
    except FileNotFoundError:
        return "error", "not found on PATH"
    except subprocess.CalledProcessError as exc:
        return "error", exc.stderr.strip() or str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return "error", str(exc)


def _check_ffmpeg() -> Tuple[str, str]:
    return _run_version(["ffmpeg", "-version"])


def _check_moviepy() -> Tuple[str, str]:
    """
    Strictly require MoviePy >= 2.x.
    Older versions using moviepy.editor are not supported.
    """
    try:
        import moviepy
        version = getattr(moviepy, "__version__", "unknown")
    except ImportError:
        return "error", "moviepy not installed (pip install moviepy)"

    # Strict validation for 2.x API
    try:
        from moviepy import VideoFileClip  # noqa: F401
    except Exception:
        return (
            "error",
            f"MoviePy {version} detected but it is not 2.x. "
            "Please reinstall: pip install moviepy>=2.0.0"
        )

    return "ok", f"moviepy {version}"

def _check_platform_config(platform_name: str, subsystem: str) -> List[Tuple[str, str, str]]:
    """
    检查特定平台的配置是否完整。
    返回检查结果列表。
    """
    checks: List[Tuple[str, str, str]] = []
    
    if not platform_name:
        checks.append((subsystem, "warn", f"{subsystem} platform not selected"))
        return checks
    
    subsystem_lower = subsystem.lower()
    
    # 检查 API key（大多数平台需要）
    api_key = config.get(platform_name, "api_key")
    
    # Google 平台特殊处理：需要 project_id 而不是 api_key
    if platform_name == "google":
        project_id = config.get("google", "project_id")
        if project_id:
            checks.append((f"{subsystem} ({platform_name})", "ok", f"project_id is set"))
        else:
            checks.append((f"{subsystem} ({platform_name})", "error", f"project_id is missing (required for Google platform)"))
        
        # Google 的 api_key 是可选的（某些服务可能需要）
        if api_key:
            checks.append((f"{subsystem} ({platform_name})", "ok", f"api_key is set (optional)"))
        else:
            checks.append((f"{subsystem} ({platform_name})", "warn", f"api_key is not set (optional for Google)"))
        
        # 检查模型配置（仅在相应的子系统下）
        if subsystem_lower == "llm":
            llm_model = config.get("google", "llm_model")
            if llm_model:
                checks.append((f"{subsystem} ({platform_name})", "ok", f"llm_model: {llm_model}"))
            else:
                checks.append((f"{subsystem} ({platform_name})", "warn", f"llm_model not set"))
    else:
        # 其他平台需要 api_key
        if api_key:
            checks.append((f"{subsystem} ({platform_name})", "ok", f"api_key is set"))
        else:
            checks.append((f"{subsystem} ({platform_name})", "error", f"api_key is missing"))
    
    # fish_audio 平台特殊处理：需要 model_id
    if platform_name == "fish_audio":
        model_id = config.get("fish_audio", "model_id")
        if model_id:
            checks.append((f"{subsystem} ({platform_name})", "ok", f"model_id is set: {model_id}"))
        else:
            checks.append((f"{subsystem} ({platform_name})", "error", f"model_id is missing (required for fish_audio)"))
    
    # 检查模型配置（如果适用）
    if subsystem_lower == "llm" and platform_name != "google":
        llm_model = config.get(platform_name, "llm_model")
        if llm_model:
            checks.append((f"{subsystem} ({platform_name})", "ok", f"llm_model: {llm_model}"))
        else:
            checks.append((f"{subsystem} ({platform_name})", "warn", f"llm_model not set"))
    
    if subsystem_lower == "text-to-video" or subsystem_lower == "text_to_video":
        if platform_name == "siliconflow":
            video_model = config.get("siliconflow", "text_video_model")
            if video_model:
                checks.append((f"{subsystem} ({platform_name})", "ok", f"text_video_model: {video_model}"))
            else:
                checks.append((f"{subsystem} ({platform_name})", "warn", f"text_video_model not set"))
    
    if subsystem_lower == "text-image" or subsystem_lower == "text_image":
        if platform_name == "google":
            image_model = config.get("google", "text_image_model")
            if image_model:
                checks.append((f"{subsystem} ({platform_name})", "ok", f"text_image_model: {image_model}"))
            else:
                checks.append((f"{subsystem} ({platform_name})", "warn", f"text_image_model not set"))
        elif platform_name == "siliconflow":
            image_model = config.get("siliconflow", "text_image_model")
            if image_model:
                checks.append((f"{subsystem} ({platform_name})", "ok", f"text_image_model: {image_model}"))
            else:
                checks.append((f"{subsystem} ({platform_name})", "warn", f"text_image_model not set"))
        elif platform_name == "openai":
            image_model = config.get("openai", "text_image_model")
            if image_model:
                checks.append((f"{subsystem} ({platform_name})", "ok", f"text_image_model: {image_model}"))
            else:
                checks.append((f"{subsystem} ({platform_name})", "warn", f"text_image_model not set"))
    
    return checks


def _check_keys() -> List[Tuple[str, str, str]]:
    """
    检查所有平台的配置。
    基于 platforms 配置中的选择，检查相应的 API keys 和其他必需配置。
    """
    checks: List[Tuple[str, str, str]] = []
    
    # 检查 LLM 平台
    llm_platform = config.get("platforms", "llm")
    checks.extend(_check_platform_config(llm_platform, "LLM"))
    
    # 检查 TTS 平台
    tts_platform = config.get("platforms", "tts")
    checks.extend(_check_platform_config(tts_platform, "TTS"))
    
    # 检查 Text-to-Video 平台
    video_platform = config.get("platforms", "text_to_video")
    checks.extend(_check_platform_config(video_platform, "Text-to-Video"))
    
    # 检查 Text-Image 平台（注意：配置中使用 "text_image" 但 platforms 中可能是 "image"）
    image_platform = config.get("platforms", "image") or config.get("platforms", "text_image")
    checks.extend(_check_platform_config(image_platform, "Text-Image"))
    
    return checks


def _print_result(name: str, status: str, detail: str) -> None:
    color = {"ok": "green", "warn": "yellow", "error": "red"}.get(status, "white")
    icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(status, "•")
    typer.secho(f"{icon} {name}: {detail}", fg=color)


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand:
        return

    _print_result("ffmpeg", *_check_ffmpeg())
    _print_result("moviepy", *_check_moviepy())

    for name, status, detail in _check_keys():
        _print_result(name, status, detail)


__all__ = ["app"]
