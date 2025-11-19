#!/usr/bin/env python3
"""
Videogen CLI helpers for the two-stage pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from videogen.pipeline.pipeline import (
    run_audio_pipeline,
    run_pipeline,
    run_video_pipeline,
)

load_dotenv()


def _resolve_project_path(project_name: str) -> Path:
    if not project_name:
        raise SystemExit("❌ project_name cannot be empty")
    path = Path(f"./project/{project_name}/{project_name}.json").resolve()
    if not path.exists():
        raise SystemExit(f"❌ Project file not found: {path}")
    return path


def _run_stage(project_name: str, runner: Callable[[Path], None], label: str) -> None:
    input_path = _resolve_project_path(project_name)
    print(f"🚀 {label} → {project_name}")
    runner(input_path)


def generate_audio(project_name: str) -> None:
    """Trigger Stage A (fish_audio only)."""
    _run_stage(project_name, run_audio_pipeline, "Audio Stage")


def generate_video(project_name: str) -> None:
    """Trigger Stage B (video actions)."""
    _run_stage(project_name, run_video_pipeline, "Video Stage")


def generate_all(project_name: str) -> None:
    """Convenience helper to run both stages sequentially."""
    _run_stage(project_name, run_pipeline, "Full Pipeline")
