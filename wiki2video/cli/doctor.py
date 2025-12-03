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

def _check_keys() -> List[Tuple[str, str, str]]:
    checks: List[Tuple[str, str, str]] = []
    llm_platform = config.get("platforms", "llm")
    llm_key = config.get_api_key(llm_platform)
    if not llm_key and (llm_platform is None or llm_platform == "siliconflow"):
        llm_key = config.get("api_keys", "siliconflow_api_key")
    if llm_platform:
        if llm_key:
            checks.append(("LLM", "ok", f"{llm_platform} API key is set"))
        else:
            checks.append(("LLM", "error", f"{llm_platform} API key is missing"))
    else:
        checks.append(("LLM", "warn", "LLM platform not selected"))

    tts_platform = config.get("platforms", "tts")
    tts_key = config.get_api_key(tts_platform)
    if not tts_key and (tts_platform is None or tts_platform == "text_audio"):
        tts_key = config.get("api_keys", "text_audio_api_key")
    if tts_platform:
        if tts_key:
            checks.append(("TTS", "ok", f"{tts_platform} API key is set"))
        else:
            checks.append(("TTS", "warn", f"{tts_platform} API key is missing"))
    else:
        checks.append(("TTS", "warn", "TTS platform not selected"))

    video_platform = config.get("platforms", "text_to_video")
    video_key = config.get_api_key(video_platform)
    if not video_key and (video_platform is None or video_platform == "siliconflow"):
        video_key = config.get("api_keys", "siliconflow_api_key")
    if video_platform:
        if video_key:
            checks.append(("Text-to-Video", "ok", f"{video_platform} API key is set"))
        else:
            checks.append(("Text-to-Video", "warn", f"{video_platform} API key is missing"))
    else:
        checks.append(("Text-to-Video", "warn", "Text-to-video platform not selected"))

    image_platform = config.get("platforms", "image")
    image_key = config.get_api_key(image_platform)
    if image_platform:
        if image_key:
            checks.append(("Image generation", "ok", f"{image_platform} API key is set"))
        else:
            checks.append(("Image generation", "warn", f"{image_platform} API key is missing"))
    else:
        checks.append(("Image generation", "warn", "Image platform not selected"))

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
