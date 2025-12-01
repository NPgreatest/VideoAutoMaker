#!/usr/bin/env python3
"""wiki2video Typer CLI entrypoint."""

from __future__ import annotations

import typer
from dotenv import load_dotenv

from wiki2video.cli import cost, doctor, generate, init, render, script

load_dotenv()

app = typer.Typer(help="wiki2video command line interface.", no_args_is_help=True)

app.add_typer(generate.app, name="generate")
app.add_typer(script.app, name="script")
app.add_typer(render.app, name="render")
app.add_typer(doctor.app, name="doctor")
app.add_typer(cost.app, name="cost")
app.add_typer(init.app, name="init")


if __name__ == "__main__":
    app()
