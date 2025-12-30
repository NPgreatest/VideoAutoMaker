#!/usr/bin/env python3
"""Rough cost estimator for a project."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from wiki2video.core.paths import get_project_json_path

app = typer.Typer(
    help="Estimate cost based on text_to_video actions inside project JSON.",
    invoke_without_command=True,
    no_args_is_help=True,
)

TEXT_TO_VIDEO_COST = 2  # $2 per text_to_video action


@app.callback()
def main(
    ctx: typer.Context,
    project_name: str = typer.Argument(..., help="Project name under ./project/"),
) -> None:
    if ctx.invoked_subcommand:
        return

    # ------------------------------
    # Load project JSON
    # ------------------------------
    json_path = get_project_json_path(project_name)
    if not json_path.exists():
        typer.secho(f"❌ {json_path} not found", fg="red", err=True)
        raise typer.Exit(code=1)

    data = json.loads(json_path.read_text())

    if "script" not in data:
        typer.secho("❌ Invalid project JSON: missing 'script' field", fg="red")
        raise typer.Exit(code=1)

    total_text_video = 0

    # ------------------------------
    # Count text_to_video actions
    # ------------------------------
    for block in data["script"]:
        actions = block.get("actions", [])
        for act in actions:
            if act.get("type") == "text_video":
                total_text_video += 1

    # ------------------------------
    # Compute cost
    # ------------------------------
    total_cost = total_text_video * TEXT_TO_VIDEO_COST

    typer.secho(f"📄 Project: {project_name}", fg="cyan")
    typer.secho(f"🎬 text_to_video count: {total_text_video}", fg="yellow")
    typer.secho(f"💰 Cost: ${total_cost}", fg="green")


__all__ = ["app"]
