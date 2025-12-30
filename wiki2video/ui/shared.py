#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from wiki2video.core.paths import get_projects_root
from wiki2video.core.utils import read_json

PROJECT_ROOT = get_projects_root()
BGM_ROOT = Path("assets/bgm")
BACKGROUND_VIDEO_ROOT = Path("assets/background_videos")

AUDIO_TABLE_COLUMNS = ["Block ID", "Text", "Duration(s)", "状态", "输出文件"]
VIDEO_TABLE_COLUMNS = ["Block ID", "Method", "状态", "输出文件"]

AUDIO_POLL_SECONDS = 10.0
VIDEO_POLL_SECONDS = 4.0

_pipeline_threads: Dict[str, threading.Thread] = {}


def list_projects() -> List[str]:
    if not PROJECT_ROOT.exists():
        return []
    projects = []
    for item in PROJECT_ROOT.iterdir():
        if not item.is_dir():
            continue
        json_path = item / f"{item.name}.json"
        if json_path.exists():
            projects.append(item.name)
    return sorted(projects, key=str.lower)


def project_json_path(project_id: str) -> Path:
    from wiki2video.core.paths import get_project_json_path
    return get_project_json_path(project_id)


def load_project_raw(project_id: str) -> Optional[Dict[str, Any]]:
    if not project_id:
        return None
    json_path = project_json_path(project_id)
    if not json_path.exists():
        return None
    try:
        return read_json(json_path)
    except FileNotFoundError:
        return None


def _resolve_paths(root: Path, patterns: List[str]) -> List[Path]:
    files: List[Path] = []
    for pattern in patterns:
        files.extend(root.glob(pattern))
    return sorted(files)


def get_bgm_choices() -> List[Tuple[str, str]]:
    choices: List[Tuple[str, str]] = [("No BGM", "")]
    if not BGM_ROOT.exists():
        return choices
    cwd = Path.cwd().resolve()
    for bgm_file in _resolve_paths(BGM_ROOT, ["*.wav", "*.mp3"]):
        display_name = bgm_file.stem
        try:
            value = str(bgm_file.resolve().relative_to(cwd))
        except ValueError:
            value = str(bgm_file)
        choices.append((display_name, value))
    return choices


def get_background_video_choices() -> List[Tuple[str, str]]:
    choices: List[Tuple[str, str]] = [("No Background Video", "")]
    if not BACKGROUND_VIDEO_ROOT.exists():
        return choices
    cwd = Path.cwd().resolve()
    video_patterns = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"]
    for video_file in _resolve_paths(BACKGROUND_VIDEO_ROOT, video_patterns):
        display_name = video_file.stem
        try:
            value = str(video_file.resolve().relative_to(cwd))
        except ValueError:
            value = str(video_file)
        choices.append((display_name, value))
    return choices


def format_text_preview(text: str, limit: int = 48) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def project_file_exists(path: Path) -> bool:
    return path.exists()


def is_pipeline_running(project_id: str) -> bool:
    thread = _pipeline_threads.get(project_id)
    return bool(thread and thread.is_alive())


def launch_pipeline_thread(project_id: str, target: Callable[[], None]) -> bool:
    if is_pipeline_running(project_id):
        return False
    thread = threading.Thread(target=target, daemon=True)
    _pipeline_threads[project_id] = thread
    thread.start()
    return True
