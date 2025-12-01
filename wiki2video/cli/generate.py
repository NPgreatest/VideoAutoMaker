#!/usr/bin/env python3
"""Generate script and render video from a wiki topic."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from wiki2video.cli.script import ScriptBuildResult, build_script
from wiki2video.pipeline.pipeline import run_pipeline

load_dotenv()

app = typer.Typer(
    help="Generate a wiki script and render the full video pipeline.",
    invoke_without_command=True,
    no_args_is_help=True,
)


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
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Accept flag for future verbose logging."
    ),
    project_name: Optional[str] = typer.Option(
        None, "--project-name", "-n", help="Override project directory name."
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Path to copy the final MP4 (default: ./out/<project>.mp4).",
    ),
) -> None:
    if ctx.invoked_subcommand:
        return

    try:
        script_result: ScriptBuildResult = build_script(
            url_or_topic,
            character=character,
            duration=duration,
            project_name=project_name,
        )
    except Exception as exc:  # pragma: no cover - CLI path
        typer.secho(f"❌ Script generation failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    typer.secho(f"📝 Script ready under project {script_result.project_name}", fg="cyan")

    try:
        run_pipeline(script_result.project_path)
    except Exception as exc:  # pragma: no cover - CLI path
        typer.secho(f"❌ Pipeline failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    final_video = _locate_final_video(script_result.project_name)
    if not final_video:
        typer.secho(
            "⚠️ Could not locate final video output. Check logs under project folder.",
            fg="yellow",
        )
        raise typer.Exit(code=1)

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = output or out_dir / f"{script_result.project_name}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_video, target)

    typer.secho(f"🎬 Final video copied to: {target}", fg="green")


__all__ = ["app"]
