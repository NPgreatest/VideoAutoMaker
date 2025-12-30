# wiki2video/cli/generate.py

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer

from wiki2video.cli.core_project_builder import ScriptBuildResult, build_project_from_wiki
from wiki2video.core.pipeline import  run_video_pipeline
from wiki2video.core.paths import get_project_dir

app = typer.Typer(
    help="Generate a video from a Wikipedia topic.",
)


def _locate_final_video(project_name: str) -> Optional[Path]:
    base = get_project_dir(project_name)
    for path in [
        base / f"{project_name}.mp4",
        base / f"{project_name}_nobgm.mp4",
        base / "_work" / "final.mp4",
    ]:
        if path.exists():
            return path
    return None


@app.command()
def generate(
    url_or_topic: str = typer.Argument(..., help="Wikipedia URL or topic"),
    size: str = typer.Option("tiktok", "--size", "-s"),
    bgm: Optional[str] = typer.Option(None, "--bgm"),
    bg_video: Optional[str] = typer.Option(None, "--bg-video"),
    burn_subtitle: bool = typer.Option(False, "--burn/--no-burn"),
    overlay: bool = typer.Option(False, "--overlay/--no-overlay"),
    project_name: Optional[str] = typer.Option(None, "--name", "-n"),
    output: Optional[Path] = typer.Option(None, "--out", "-o"),
):
    """Generate script + project.json and render final video."""

    typer.secho("🚀 Starting Wiki → Video full pipeline...", fg="cyan")

    # Step 1 — Build project
    try:
        script_result: ScriptBuildResult = build_project_from_wiki(
            wiki_input=url_or_topic,
            project_name=project_name,
            size=size,
            bgm=bgm,
            bg_video=bg_video,
            burn=burn_subtitle,
            show_overlay=overlay,
        )
    except Exception as exc:
        typer.secho(f"❌ Script generation failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    typer.secho(f"📘 Project JSON created: {script_result.project_path}", fg="cyan")

    # Step 2 — Render pipeline
    try:
        run_video_pipeline(script_result.project_name)
    except Exception as exc:
        typer.secho(f"❌ Render pipeline failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)

    # Step 3 — Find final mp4
    final_video = _locate_final_video(script_result.project_name)
    if not final_video:
        typer.secho("⚠️ Could not find final video output.", fg="yellow")
        raise typer.Exit(code=1)

    # Step 4 — Copy to user-visible location (CWD by default)
    cwd = Path.cwd()

    if output:
        # --out can be either a file or a directory
        if output.is_dir() or output.suffix == "":
            target = output / f"{script_result.project_name}.mp4"
        else:
            target = output
    else:
        target = cwd / f"{script_result.project_name}.mp4"

    shutil.copy2(final_video, target)
    typer.secho(f"🎬 Final video saved to: {target}", fg="green")


__all__ = ["app"]
