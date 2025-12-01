#!/usr/bin/env python3
"""Render a video from an existing script JSON."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.pipeline.pipeline import run_pipeline
from wiki2video.pipeline.utils import read_json

load_dotenv()

app = typer.Typer(
    help="Render a video from a prepared script JSON file.",
    invoke_without_command=True,
    no_args_is_help=True,
)


def _reset_working_blocks(project_name: str) -> None:
    dao = WorkingBlockDAO()
    for wb in dao.get_all(project_name):
        dao.delete(wb.id)


def _locate_final_video(project_name: str) -> Optional[Path]:
    base = Path("project") / project_name
    candidates = [
        base / f"{project_name}.mp4",
        base / f"{project_name}_nobgm.mp4",
        base / "_work" / "final.mp4",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _mirror_to_project_dir(src: Path, project_name: str) -> Path:
    project_dir = Path("project") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / f"{project_name}.json"
    if src.resolve() != target.resolve():
        shutil.copy2(src, target)
    return target


@app.callback()
def main(
    ctx: typer.Context,
    script_path: Path = typer.Argument(..., help="Path to script JSON."),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Path to copy the final MP4 (default: ./out/<project>.mp4).",
    ),
) -> None:
    if ctx.invoked_subcommand:
        return

    path = script_path.expanduser().resolve()
    if not path.exists():
        typer.secho(f"❌ Script file not found: {path}", fg="red", err=True)
        raise typer.Exit(code=1)

    try:
        raw = read_json(path)
    except Exception as exc:  # pragma: no cover - CLI path
        typer.secho(f"❌ Failed to read JSON: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    project_name = raw.get("project_name")
    if not project_name:
        typer.secho("❌ project_name missing in JSON", fg="red", err=True)
        raise typer.Exit(code=1)

    canonical_path = _mirror_to_project_dir(path, project_name)
    _reset_working_blocks(project_name)

    try:
        run_pipeline(canonical_path)
    except Exception as exc:  # pragma: no cover - CLI path
        typer.secho(f"❌ Pipeline failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    # Keep original JSON in sync with updated status
    try:
        shutil.copy2(canonical_path, path)
    except Exception:
        pass

    final_video = _locate_final_video(project_name)
    if not final_video:
        typer.secho("⚠️ Could not locate final video output.", fg="yellow")
        raise typer.Exit(code=1)

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out or out_dir / f"{project_name}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_video, target)

    typer.secho(f"🎬 Final video copied to: {target}", fg="green")


__all__ = ["app"]
