#!/usr/bin/env python3
"""wiki2video Typer CLI entrypoint."""

from __future__ import annotations

import typer
from dotenv import load_dotenv

from wiki2video.cli import cost, doctor, init, render
from wiki2video.cli.script import script_command
from wiki2video.cli.generate import generate  # <-- import the command function

load_dotenv()

app = typer.Typer(help="wiki2video command line interface.", no_args_is_help=True)

# Top-level commands
app.command("script")(script_command)
app.command("generate")(generate)

# Other multi-command groups
app.add_typer(render.app, name="render")
app.add_typer(doctor.app, name="doctor")
app.add_typer(cost.app, name="cost")
app.add_typer(init.app, name="init")


if __name__ == "__main__":
    app()
