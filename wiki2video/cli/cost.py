#!/usr/bin/env python3
"""Rough cost estimator for a project."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    help="Estimate cost from a project's script.txt line count.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    project_name: str = typer.Argument(..., help="Project name under ./project/"),
) -> None:
    if ctx.invoked_subcommand:
        return

    script_path = Path("project") / project_name / "script.txt"
    if not script_path.exists():
        typer.secho(f"❌ script.txt not found at {script_path}", fg="red", err=True)
        raise typer.Exit(code=1)

    with open(script_path, "r", encoding="utf-8") as f:
        lines = [line for line in f.readlines() if line.strip()]
    cost = len(lines) * 2
    typer.secho(f"Lines: {len(lines)} · Estimated cost: ${cost}", fg="green")


__all__ = ["app"]
