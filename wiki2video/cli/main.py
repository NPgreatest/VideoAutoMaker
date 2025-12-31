#!/usr/bin/env python3
"""wiki2video Typer CLI entrypoint."""

from __future__ import annotations

import json
from typing import List

import typer

from wiki2video.cli import cost, doctor, init, render
from wiki2video.cli.generate import generate  # <-- import the command function
from wiki2video.cli.script import script_command
from wiki2video.config.config_manager import CONFIG_FILE, SUPPORTED_PLATFORMS, config

app = typer.Typer(help="wiki2video command line interface.", no_args_is_help=True)


@app.command("config")
def config_command(
    set_values: List[str] = typer.Option(
        None,
        "--set",
        "-s",
        help="Update configuration via section.key=value (e.g. platforms.llm=openai).",
        metavar="KEY=VALUE",
    ),
    show: bool = typer.Option(False, "--show", help="Print the current configuration."),
) -> None:
    """
    Inspect or update wiki2video config.json.
    """
    if not set_values and not show:
        typer.echo(f"Config file: {CONFIG_FILE}")
        typer.echo(
            "Use --show to print it or --set section.key=value to update. "
            f"Platform options: {SUPPORTED_PLATFORMS}"
        )
        raise typer.Exit(code=0)

    if set_values:
        for item in set_values:
            if "=" not in item:
                typer.secho(f"Invalid --set value (missing '='): {item}", fg="red", err=True)
                raise typer.Exit(code=1)
            path, raw_value = item.split("=", 1)
            keys = path.split(".")
            try:
                config.set(*keys, value=raw_value)
                typer.secho(f"Updated {'/'.join(keys)}", fg="green")
            except ValueError as exc:
                typer.secho(f"❌ {exc}", fg="red", err=True)
                raise typer.Exit(code=1)

    if show:
        typer.echo(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))


# Top-level commands
# app.command("script")(script_command)
app.command("generate")(generate)

# Other multi-command groups
# app.add_typer(render.app, name="render")
app.add_typer(doctor.app, name="doctor")
# app.add_typer(cost.app, name="cost")
app.add_typer(init.app, name="init")


if __name__ == "__main__":
    app()
