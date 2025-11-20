#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from videogen.pipeline.utils import load_character_config, read_json

PROJECT_ROOT = Path("project")
BGM_ROOT = Path("assets/bgm")
BACKGROUND_VIDEO_ROOT = Path("assets/background_videos")

AUDIO_TABLE_COLUMNS = ["Block ID", "Character", "Text", "Duration(s)", "状态", "输出文件"]
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


def project_json_path(project_name: str) -> Path:
    return PROJECT_ROOT / project_name / f"{project_name}.json"


def load_project_raw(project_name: str) -> Optional[Dict[str, Any]]:
    if not project_name:
        return None
    json_path = project_json_path(project_name)
    if not json_path.exists():
        return None
    try:
        return read_json(json_path)
    except FileNotFoundError:
        return None


def get_character_choices() -> List[Tuple[str, str]]:
    config = load_character_config()
    choices: List[Tuple[str, str]] = []
    for key, value in config.items():
        display_name = value.get("name") or key
        label = f"{display_name} ({key})" if display_name != key else key
        choices.append((label, key))
    choices.sort(key=lambda x: x[0])
    return choices


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


def is_pipeline_running(project_name: str) -> bool:
    thread = _pipeline_threads.get(project_name)
    return bool(thread and thread.is_alive())


def launch_pipeline_thread(project_name: str, target: Callable[[], None]) -> bool:
    if is_pipeline_running(project_name):
        return False
    thread = threading.Thread(target=target, daemon=True)
    _pipeline_threads[project_name] = thread
    thread.start()
    return True


