#!/usr/bin/env python3
"""First-time configuration setup for wiki2video."""

from __future__ import annotations

from typing import Any, Dict, Optional

import typer

from wiki2video.config.config_manager import config
from wiki2video.config.default_config import _default_config

app = typer.Typer(
    help="First-time configuration setup for wiki2video.",
    invoke_without_command=True,
)


# -----------------------------
# Prompt helpers
# -----------------------------

def _prompt_choice(
    prompt: str,
    choices: list[str],
    default: Optional[str] = None,
    recommended: Optional[str] = None,
) -> str:
    """Interactive choice prompt."""
    while True:
        typer.echo(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            tags = []
            if choice == default:
                tags.append("default")
            if choice == recommended:
                tags.append("recommended")
            suffix = f" ({', '.join(tags)})" if tags else ""
            typer.echo(f"  {i}. {choice}{suffix}")

        default_hint = f" [{default}]" if default else ""
        user_input = typer.prompt(
            f"Select an option{default_hint}",
            default=default or "",
        )

        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(choices):
                return choices[idx]

        if user_input in choices:
            return user_input

        typer.secho(
            "❌ Invalid choice. Please enter a number or the option name.",
            fg="red",
        )


def _prompt_input(
    prompt: str,
    default: Optional[str] = None,
    required: bool = True,
) -> Optional[str]:
    """Interactive text input prompt."""
    suffix = " (required)" if required else " (optional)"
    default_hint = f" [{default}]" if default else ""

    while True:
        value = typer.prompt(
            f"{prompt}{suffix}{default_hint}",
            default=default or "",
        )
        if value.strip() or not required:
            return value.strip() if value.strip() else None
        typer.secho("❌ This field is required.", fg="red")


# -----------------------------
# Platform setup helpers
# -----------------------------

def _get_platform_config_keys(platform: str) -> Dict[str, Any]:
    default = _default_config()
    return default.get(platform, {})


def _setup_platform_config(platform: str) -> None:
    """Configure credentials for a specific platform."""
    typer.secho(f"\n📝 Configure platform: {platform}", fg="cyan", bold=True)

    if platform == "google":
        project_id = _prompt_input("Google Project ID", required=True)
        if project_id:
            config.set("google", "project_id", value=project_id)

        api_key = _prompt_input("Google API Key", required=False)
        if api_key:
            config.set("google", "api_key", value=api_key)

        output_gcs_uri = _prompt_input(
            "Google Cloud Storage output URI",
            required=False,
        )
        if output_gcs_uri:
            config.set("google", "output_gcs_uri", value=output_gcs_uri)

        cx_key = _prompt_input(
            "Google Custom Search API Key",
            required=False,
        )
        if cx_key:
            config.set("google", "cx_key", value=cx_key)

    elif platform == "fish_audio":
        api_key = _prompt_input("Fish Audio API Key", required=True)
        if api_key:
            config.set("fish_audio", "api_key", value=api_key)

        model_id = _prompt_input("Fish Audio Model ID", required=True)
        if model_id:
            config.set("fish_audio", "model_id", value=model_id)

    else:
        api_key = _prompt_input(f"{platform.upper()} API Key", required=True)
        if api_key:
            config.set(platform, "api_key", value=api_key)


def _setup_platforms(generate_mode: str, main_platform: str) -> None:
    """Configure subsystem platforms based on mode and main platform."""
    if generate_mode == "video":
        if main_platform == "openai":
            config.set("platforms", "text_to_video", value="openai")
            config.set("platforms", "llm", value="openai")
            config.set("platforms", "tts", value="openai")
            config.set("platforms", "text_image", value="openai")

        elif main_platform == "siliconflow":
            config.set("platforms", "text_to_video", value="siliconflow")
            config.set("platforms", "llm", value="siliconflow")
            config.set("platforms", "tts", value="google")
            config.set("platforms", "text_image", value="siliconflow")

        elif main_platform == "google":
            config.set("platforms", "text_to_video", value="siliconflow")
            config.set("platforms", "llm", value="google")
            config.set("platforms", "tts", value="google")
            config.set("platforms", "text_image", value="google")

    else:
        # image mode
        config.set("platforms", "llm", value=main_platform)
        config.set(
            "platforms",
            "tts",
            value="openai" if main_platform == "openai" else "google",
        )
        config.set("platforms", "text_image", value=main_platform)


# -----------------------------
# Summary & doctor
# -----------------------------

def _print_config_summary() -> None:
    typer.secho("\n" + "=" * 60, fg="cyan")
    typer.secho("📋 Configuration Summary", fg="cyan", bold=True)
    typer.secho("=" * 60, fg="cyan")

    cfg = config.to_dict()

    typer.echo(f"\nGeneration mode: {cfg.get('generate_mode', 'N/A')}")

    typer.echo("\nPlatforms:")
    for k, v in cfg.get("platforms", {}).items():
        typer.echo(f"  {k}: {v}")

    typer.echo("\nCredentials:")
    for name in ["openai", "siliconflow", "google", "fish_audio"]:
        section = cfg.get(name, {})
        api_key = section.get("api_key")
        if api_key:
            masked = (
                api_key[:8] + "..." + api_key[-4:]
                if len(api_key) > 12
                else "***"
            )
            typer.echo(f"  {name}: api_key = {masked}")

        if name == "google" and section.get("project_id"):
            typer.echo(f"  google: project_id = {section['project_id']}")

        if name == "fish_audio" and section.get("model_id"):
            typer.echo(f"  fish_audio: model_id = {section['model_id']}")

    typer.secho("\n" + "=" * 60, fg="cyan")


def _run_doctor() -> None:
    typer.secho("\n🔍 Running environment checks...", fg="cyan", bold=True)
    try:
        from wiki2video.cli.doctor import (
            _check_ffmpeg,
            _check_moviepy,
            _check_keys,
            _print_result,
        )

        _print_result("ffmpeg", *_check_ffmpeg())
        _print_result("moviepy", *_check_moviepy())

        for name, status, detail in _check_keys():
            _print_result(name, status, detail)

    except Exception as e:
        typer.secho(f"⚠️  Doctor failed: {e}", fg="yellow")
        typer.secho("💡 You can retry later with `wiki2video doctor`", fg="cyan")


# -----------------------------
# Main wizard
# -----------------------------

@app.callback()
def main(ctx: typer.Context) -> None:
    """First-time setup wizard."""
    if ctx.invoked_subcommand:
        return

    typer.secho("\n" + "=" * 60, fg="green", bold=True)
    typer.secho("🚀 Wiki2Video First-Time Setup Wizard", fg="green", bold=True)
    typer.secho("=" * 60, fg="green")

    # Step 1: generation mode
    typer.secho("\n🖼️  Step 1: Select generation mode", fg="cyan", bold=True)
    generate_mode = _prompt_choice(
        "Choose generation mode",
        choices=["image", "video"],
        default="image",
    )
    config.set("generate_mode", value=generate_mode)
    typer.secho(f"✅ Generation mode set to: {generate_mode}", fg="green")

    # Step 2: main platform
    typer.secho("\n🔌 Step 2: Select main platform", fg="cyan", bold=True)
    typer.echo("Tip: OpenAI is recommended for best overall support.")
    main_platform = _prompt_choice(
        "Choose main platform",
        choices=["openai", "siliconflow", "google"],
        default="openai",
        recommended="openai",
    )
    typer.secho(f"✅ Main platform: {main_platform}", fg="green")

    # Step 3: credentials
    typer.secho("\n🔑 Step 3: Configure credentials", fg="cyan", bold=True)
    _setup_platform_config(main_platform)

    if generate_mode == "video":
        if main_platform == "google":
            typer.secho(
                "\n⚠️  Google does not support video generation directly.",
                fg="yellow",
            )
            if typer.confirm(
                "Configure SiliconFlow for video generation?",
                default=True,
            ):
                _setup_platform_config("siliconflow")

        if main_platform in ("siliconflow", "google"):
            if typer.confirm("Configure Google TTS?", default=True):
                _setup_platform_config("google")

    # Step 4: subsystem mapping
    _setup_platforms(generate_mode, main_platform)

    # Step 5: summary
    _print_config_summary()

    typer.secho("\n💡 Notes:", fg="yellow", bold=True)
    typer.echo(f"  Config file: {config.config_file}")
    typer.echo("  You can edit it manually at any time.")

    typer.secho("\n" + "=" * 60, fg="green")
    if typer.confirm("Run environment checks now?", default=True):
        _run_doctor()
    else:
        typer.secho(
            "💡 You can run checks later with `wiki2video doctor`",
            fg="cyan",
        )

    typer.secho("\n✅ Setup complete!", fg="green", bold=True)


__all__ = ["app"]
