# wiki2video/cli/core_project_builder.py
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from wiki2video.core.paths import get_projects_root, get_project_dir, get_project_json_path
from wiki2video.core.parse_script import parse_script_lines
from wiki2video.core.utils import write_json
from wiki2video.schema.project_schema import ScriptBlock, ProjectStatus
from wiki2video.llm_agent.agents.wiki2video.wiki2video_interactive import (
    Wiki2VideoInteractiveOrchestrator,
)

def _slugify_topic(text: str) -> str:
    import re
    base = re.sub(r"https?://", "", text.strip().lower())
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "wiki2video"

def _resolve_project_name(topic: str, override: Optional[str]) -> str:
    base = (_slugify_topic(override) if override else _slugify_topic(topic))[:48]
    suffix = time.strftime("%Y%m%d-%H%M%S") if not override else ""
    candidate = f"{base}-{suffix}" if suffix else base or "wiki2video"

    project_root = get_projects_root()
    idx = 1
    while (project_root / candidate).exists():
        idx += 1
        candidate = f"{base}-{suffix}-{idx}" if suffix else f"{base}-{idx}"
    return candidate

async def _generate_script_and_context(wiki_input: str, project_name: str):
    oc = Wiki2VideoInteractiveOrchestrator()
    return await oc.run_full(wiki_input, project_name)

@dataclass
class ScriptBuildResult:
    project_name: str
    project_path: Path
    script_text: str
    blocks: List[ScriptBlock]
    global_context: str

def build_project_from_wiki(
    wiki_input: str,
    *,
    project_name: Optional[str],
    size: str,
    bgm: Optional[str],
    bg_video: Optional[str],
    burn: bool,
    show_overlay: bool,
) -> ScriptBuildResult:

    project_name = _resolve_project_name(wiki_input, project_name)

    script_text, global_context = asyncio.run(
        _generate_script_and_context(wiki_input, project_name)
    )

    blocks = parse_script_lines(
        script_text,
        size,
        bg_video,
        show_overlay,
    )
    if not blocks:
        raise RuntimeError("Failed to parse script into blocks.")

    project_dir = get_project_dir(project_name)

    # save script.txt
    (project_dir / "script.txt").write_text(script_text, encoding="utf-8")

    # save project.json
    payload: Dict[str, Any] = {
        "project_name": project_name,
        "size": size,
        "script": [asdict(b) for b in blocks],
        "project_status": ProjectStatus.CREATED.value,
        "global_context": global_context,
        "show_character_overlay": bool(show_overlay),
        "bgm_path": bgm,
        "background_video": bg_video,
        "burn_subtitle": bool(burn),
        "source": wiki_input,
    }

    json_path = get_project_json_path(project_name)
    write_json(json_path, payload)

    return ScriptBuildResult(
        project_name=project_name,
        project_path=json_path,
        script_text=script_text,
        blocks=blocks,
        global_context=global_context,
    )



def build_project_from_script(
    script_text: str,
    project_name: Optional[str],
    *,
    size: str,
    bgm: Optional[str],
    bg_video: Optional[str],
    burn: bool,
    show_overlay: bool,
    global_context: str,
) -> ScriptBuildResult:

    blocks = parse_script_lines(
        script_text,
        size,
        bg_video,
        show_overlay,
    )
    if not blocks:
        raise RuntimeError("Failed to parse script into blocks.")

    project_dir = get_project_dir(project_name)

    # save script.txt
    (project_dir / "script.txt").write_text(script_text, encoding="utf-8")

    # save project.json
    payload: Dict[str, Any] = {
        "project_name": project_name,
        "size": size,
        "script": [asdict(b) for b in blocks],
        "project_status": ProjectStatus.CREATED.value,
        "global_context": global_context,
        "show_character_overlay": bool(show_overlay),
        "bgm_path": bgm,
        "background_video": bg_video,
        "burn_subtitle": bool(burn),
    }

    json_path = get_project_json_path(project_name)
    write_json(json_path, payload)

    return ScriptBuildResult(
        project_name=project_name,
        project_path=json_path,
        script_text=script_text,
        blocks=blocks,
        global_context=global_context,
    )
