#!/usr/bin/env python3
"""Generate wiki-driven scripts without rendering the video."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from dotenv import load_dotenv

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.llm_agent.agents.utils.script_normalizer import normalize_script
from wiki2video.llm_agent.agents.wiki2video.wiki2video_interactive import (
    Wiki2VideoInteractiveOrchestrator,
    _ask_llm,
    _render_prompt,
    loader,
)
from wiki2video.pipeline.parse_script import parse_script_lines
from wiki2video.pipeline.utils import load_character_config, write_json
from wiki2video.schema.project_schema import ProjectStatus, ScriptBlock

load_dotenv()

app = typer.Typer(
    help="Generate a structured script JSON from a Wikipedia URL or topic.",
    invoke_without_command=True,
    no_args_is_help=True,
)

DEFAULT_SIZE = "tiktok"

# Map character shortcuts to prompt template keys.
SCRIPT_PROMPT_MAP = {
    "elon": "elon_trump",
    "trump": "elon_trump",
    "elon_trump": "elon_trump",
    "stewie": "stewie_peter",
    "peter": "stewie_peter",
    "stewie_peter": "stewie_peter",
    "leijun": "leijun_dingzhen",
    "dingzhen": "leijun_dingzhen",
    "leijun_dingzhen": "leijun_dingzhen",
    "manbo": "leijun_manbo",
    "leijun_manbo": "leijun_manbo",
}


@dataclass
class ScriptBuildResult:
    project_name: str
    script_text: str
    blocks: List[ScriptBlock]
    direction: Optional[str]
    cleaned_wiki: Dict[str, Any]
    project_path: Path
    script_txt_path: Path
    prompt_key: str
    target_duration: Optional[int]


def _slugify_topic(text: str) -> str:
    base = re.sub(r"https?://", "", text.strip().lower())
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "wiki2video"


def _resolve_project_name(topic: str, override: Optional[str]) -> str:
    base = (_slugify_topic(override) if override else _slugify_topic(topic))[:48] or "wiki2video"
    suffix = time.strftime("%Y%m%d-%H%M%S") if not override else ""
    candidate = f"{base}-{suffix}" if suffix else base
    project_root = Path("project")
    idx = 1
    while (project_root / candidate).exists():
        idx += 1
        candidate = f"{base}-{suffix}-{idx}" if suffix else f"{base}-{idx}"
    return candidate


def _select_prompt_key(character: Optional[str]) -> str:
    if not character:
        return "wiki_solo_narrative"
    key = character.strip().lower()
    return SCRIPT_PROMPT_MAP.get(key, "wiki_solo_narrative")


def _default_character(character: Optional[str]) -> str:
    if character:
        return character
    cfg = load_character_config()
    if cfg:
        return sorted(cfg.keys())[0]
    return "narrator"


def _reset_working_blocks(project_name: str) -> None:
    dao = WorkingBlockDAO()
    for wb in dao.get_all(project_name):
        dao.delete(wb.id)


async def _generate_script_text(
    wiki_input: str,
    project_name: str,
    prompt_key: str,
    duration: Optional[int],
) -> tuple[str, str, Dict[str, Any]]:
    orchestrator = Wiki2VideoInteractiveOrchestrator()
    cleaned = orchestrator.fetcher_cleaner.run(wiki_input, project_name)

    direction_template = loader.load_from_registry("wiki_direction_extractor", "default")
    direction_prompt = direction_template.replace(
        "{WIKI_JSON}", json.dumps(cleaned["sections"], ensure_ascii=False)
    )
    direction = await _ask_llm(direction_prompt)

    script_prompt = _render_prompt(
        "script_structure",
        prompt_key,
        USER_SELECTED_DIRECTION_JSON=direction,
        CLEANED_TEXT=cleaned["clean_text"],
    )
    if duration:
        script_prompt = (
            f"Target final runtime: about {duration} minutes.\n\n" + script_prompt
        )

    script_raw = await _ask_llm(script_prompt)

    insert_prompt = _render_prompt(
        "insert_image",
        "local",
        SCRIPT_TEXT=script_raw,
        IMAGE_SUMMARY=cleaned["images"],
    )
    script_final = await _ask_llm(insert_prompt)
    normalized_script = normalize_script(script_final)
    return normalized_script, direction, cleaned


def build_script(
    wiki_input: str,
    *,
    character: Optional[str] = None,
    duration: Optional[int] = None,
    project_name: Optional[str] = None,
) -> ScriptBuildResult:
    prompt_key = _select_prompt_key(character)
    project_name = _resolve_project_name(wiki_input, project_name)
    duration_val = duration if duration and duration > 0 else None
    default_character = _default_character(character)

    script_text, direction, cleaned = asyncio.run(
        _generate_script_text(wiki_input, project_name, prompt_key, duration_val)
    )

    blocks = parse_script_lines(
        script_text,
        default_character,
        size=DEFAULT_SIZE,
        background_video=None,
        show_character_overlay=True,
    )
    if not blocks:
        raise RuntimeError("Failed to parse script into blocks.")

    _reset_working_blocks(project_name)

    project_dir = Path("project") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    script_txt_path = project_dir / "script.txt"
    script_txt_path.write_text(script_text, encoding="utf-8")

    payload: Dict[str, Any] = {
        "project_name": project_name,
        "project_status": ProjectStatus.CREATED.value,
        "script": [asdict(b) for b in blocks],
        "size": DEFAULT_SIZE,
        "global_context": direction,
        "show_character_overlay": True,
        "bgm_path": None,
        "background_video": None,
        "burn_subtitle": True,
        "source": wiki_input,
        "script_prompt_key": prompt_key,
    }
    if duration_val:
        payload["target_duration_minutes"] = duration_val

    project_path = project_dir / f"{project_name}.json"
    write_json(project_path, payload)

    return ScriptBuildResult(
        project_name=project_name,
        script_text=script_text,
        blocks=blocks,
        direction=direction,
        cleaned_wiki=cleaned,
        project_path=project_path,
        script_txt_path=script_txt_path,
        prompt_key=prompt_key,
        target_duration=duration_val,
    )


@app.callback()
def main(
    ctx: typer.Context,
    url_or_topic: str = typer.Argument(..., help="Wikipedia URL or topic"),
    character: Optional[str] = typer.Option(
        None, "--character", "-c", help="Character voice / script style key."
    ),
    duration: Optional[int] = typer.Option(
        None, "--duration", "-d", help="Approximate target duration in minutes."
    ),
    project_name: Optional[str] = typer.Option(
        None, "--project-name", "-n", help="Override project directory name."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Print extra generation details (accepted, not required)."
    ),
) -> None:
    if ctx.invoked_subcommand:
        return
    try:
        result = build_script(
            url_or_topic,
            character=character,
            duration=duration,
            project_name=project_name,
        )
    except Exception as exc:  # pragma: no cover - CLI path
        typer.secho(f"❌ Script generation failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "script.json"
    shutil.copy2(result.project_path, out_path)

    typer.secho(f"📄 Script saved: {out_path}", fg="green")
    typer.secho(f"📁 Project folder: {result.project_path.parent}", fg="cyan")
    if result.direction and verbose:
        typer.echo(f"🧭 Direction: {result.direction}")


__all__ = ["app", "build_script", "ScriptBuildResult"]
