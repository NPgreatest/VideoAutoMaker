#!/usr/bin/env python3
"""Interactive project initializer."""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.pipeline.parse_script import parse_script_lines
from wiki2video.pipeline.utils import load_character_config, write_json
from wiki2video.schema.project_schema import ProjectStatus

load_dotenv()

app = typer.Typer(
    help="Create a project by pasting a script manually.",
    invoke_without_command=True,
    no_args_is_help=True,
)


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


def _sanitize_project_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-")
    return slug or "project"


@app.callback()
def main(
    ctx: typer.Context,
    project_name: str = typer.Argument(..., help="Name for ./project/<project_name>/"),
    character: Optional[str] = typer.Option(
        None, "--character", "-c", help="Default speaker when no prefix is provided."
    ),
    size: str = typer.Option(
        "tiktok",
        "--size",
        "-s",
        help="Video format: tiktok (portrait) or landscape.",
    ),
    background_video: Optional[str] = typer.Option(
        None, "--background-video", help="Optional background video path."
    ),
    show_character_overlay: bool = typer.Option(
        True, "--overlay/--no-overlay", help="Include character overlay layers."
    ),
) -> None:
    if ctx.invoked_subcommand:
        return

    project_name = _sanitize_project_name(project_name)
    project_dir = Path("project") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    existing_json = project_dir / f"{project_name}.json"
    if existing_json.exists():
        typer.secho(
            f"❌ Project already exists at {existing_json}. Choose another name.",
            fg="red",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo("Enter your script line by line. Type 'EOF' on a new line to finish.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "EOF":
            break
        lines.append(line)

    script_text = "\n".join(lines).strip()
    if not script_text:
        typer.secho("❌ No script text provided.", fg="red", err=True)
        raise typer.Exit(code=1)

    default_character = _default_character(character)
    blocks = parse_script_lines(
        script_text,
        default_character,
        size=size,
        background_video=background_video,
        show_character_overlay=show_character_overlay,
    )
    if not blocks:
        typer.secho("❌ Failed to parse script text.", fg="red", err=True)
        raise typer.Exit(code=1)

    _reset_working_blocks(project_name)

    script_txt_path = project_dir / "script.txt"
    script_txt_path.write_text(script_text, encoding="utf-8")

    payload = {
        "project_name": project_name,
        "project_status": ProjectStatus.CREATED.value,
        "script": [asdict(b) for b in blocks],
        "size": size,
        "show_character_overlay": show_character_overlay,
        "bgm_path": None,
        "background_video": background_video,
        "burn_subtitle": True,
        "source": "manual",
    }

    canonical_path = project_dir / f"{project_name}.json"
    write_json(canonical_path, payload)
    write_json(project_dir / "project.json", payload)

    typer.secho(f"✅ Project saved to {canonical_path}", fg="green")
    typer.secho("Run `wiki2video render project/<name>.json` to start rendering.", fg="cyan")


__all__ = ["app"]
