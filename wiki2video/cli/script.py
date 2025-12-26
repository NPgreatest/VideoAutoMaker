# wiki2video/cli/script.py

from __future__ import annotations
import typer
from pathlib import Path
from typing import Optional

from wiki2video.cli.core_project_builder import build_project_from_wiki, ScriptBuildResult

def script_command(
    wiki: str = typer.Argument(..., help="Wikipedia URL or topic"),

    project_name: Optional[str] = typer.Option(None, "--name", "-n"),
    size: str = typer.Option("tiktok", "--size", "-s"),
    bgm: Optional[str] = typer.Option(None, "--bgm"),
    bg_video: Optional[str] = typer.Option(None, "--bg-video"),
    burn: bool = typer.Option(True, "--burn/--no-burn"),
    show_overlay: bool = typer.Option(True, "--overlay/--no-overlay"),
):
    typer.secho("🚀 Running full Wiki → Video pipeline...", fg="cyan")

    try:
        result: ScriptBuildResult = build_project_from_wiki(
            wiki_input=wiki,
            project_name=project_name,
            size=size,
            bgm=bgm,
            bg_video=bg_video,
            burn=burn,
            show_overlay=show_overlay,
        )
    except Exception as exc:
        typer.secho(f"❌ Failed: {exc}", fg="red")
        raise typer.Exit(code=1)

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    out_json = out_dir / "script.json"
    out_json.write_text(result.script_text, encoding="utf-8")

    typer.secho(f"📄 Project created: {result.project_path}", fg="green")

app = typer.Typer()
app.command()(script_command)
