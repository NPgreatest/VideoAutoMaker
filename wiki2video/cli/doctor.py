#!/usr/bin/env python3
"""Environment checks for wiki2video."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Tuple

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    help="Verify local dependencies and API keys.",
    invoke_without_command=True,
    no_args_is_help=True,
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


def _check_node() -> Tuple[str, str]:
    return _run_version(["node", "-v"])


def _check_remotion_env() -> Tuple[str, str]:
    project_dir = Path("videogen/methods/remotion_animation/remotion_project")
    pkg = project_dir / "package.json"
    node_modules = project_dir / "node_modules"
    if not pkg.exists():
        return "error", f"package.json missing under {project_dir}"
    if not node_modules.exists():
        return "warn", f"Install dependencies in {project_dir} (npm install)"
    return "ok", "package.json and node_modules detected"


def _check_keys() -> List[Tuple[str, str, str]]:
    checks: List[Tuple[str, str, str]] = []
    silicon = os.getenv("SILICONFLOW_API_TOKEN")
    audio_fish = os.getenv("AUDIO_FISH_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if silicon:
        checks.append(("SiliconFlow API", "ok", "SILICONFLOW_API_TOKEN is set"))
    else:
        checks.append(("SiliconFlow API", "error", "SILICONFLOW_API_TOKEN is missing"))

    if audio_fish:
        checks.append(("AudioFish", "ok", "AUDIO_FISH_API_KEY is set"))
    else:
        checks.append(("AudioFish", "warn", "AUDIO_FISH_API_KEY is missing"))

    if openai_key:
        checks.append(("OpenAI (optional)", "ok", "OPENAI_API_KEY is set"))
    else:
        checks.append(("OpenAI (optional)", "warn", "OPENAI_API_KEY not set"))

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
    _print_result("node", *_check_node())
    _print_result("Remotion", *_check_remotion_env())

    for name, status, detail in _check_keys():
        _print_result(name, status, detail)


__all__ = ["app"]
