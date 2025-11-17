#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
import pandas as pd

from videogen.cli.generate import generate_video
from videogen.pipeline.utils import (
    load_character_config,
    read_json,
    write_json,
    get_project_status,
)
from videogen.pipeline.schema import ProjectStatus
from videogen.pipeline.parse_script import parse_script_lines


PROJECT_ROOT = Path("project")
BGM_ROOT = Path("assets/bgm")
BACKGROUND_VIDEO_ROOT = Path("assets/background_videos")
STATUS_COLUMNS = ["ID", "Character", "Text", "Audio", "Video", "Status"]


_pipeline_threads: Dict[str, threading.Thread] = {}


def list_projects() -> List[str]:
    if not PROJECT_ROOT.exists():
        return []
    projects: List[str] = []
    for item in PROJECT_ROOT.iterdir():
        if item.is_dir():
            json_path = item / f"{item.name}.json"
            if json_path.exists():
                projects.append(item.name)
    return sorted(projects, key=str.lower)


def get_character_choices() -> List[Tuple[str, str]]:
    config = load_character_config()
    choices: List[Tuple[str, str]] = []
    for key, value in config.items():
        display_name = value.get("name") or key
        label = f"{display_name} ({key})" if display_name != key else key
        choices.append((label, key))
    choices.sort(key=lambda x: x[0])
    return choices


def get_bgm_choices() -> List[Tuple[str, str]]:
    """Scan BGM directory and return list of (display_name, file_path) tuples."""
    choices: List[Tuple[str, str]] = [("No BGM", "")]
    if not BGM_ROOT.exists():
        return choices
    
    cwd_resolved = Path.cwd().resolve()
    bgm_files = sorted(BGM_ROOT.glob("*.wav"))
    
    for bgm_file in bgm_files:
        # Use filename without extension as display name
        display_name = bgm_file.stem
        # Store relative path from project root
        try:
            bgm_path = str(bgm_file.resolve().relative_to(cwd_resolved))
        except ValueError:
            # If relative_to fails, use the path as-is (shouldn't happen in normal cases)
            bgm_path = str(bgm_file)
        choices.append((display_name, bgm_path))
    
    return choices


def get_background_video_choices() -> List[Tuple[str, str]]:
    """Scan background video directory and return list of (display_name, file_path) tuples."""
    choices: List[Tuple[str, str]] = [("No Background Video", "")]
    if not BACKGROUND_VIDEO_ROOT.exists():
        return choices
    
    cwd_resolved = Path.cwd().resolve()
    # Support common video formats
    video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"]
    video_files = []
    for ext in video_extensions:
        video_files.extend(BACKGROUND_VIDEO_ROOT.glob(ext))
    
    video_files = sorted(video_files)
    
    for video_file in video_files:
        # Use filename without extension as display name
        display_name = video_file.stem
        # Store relative path from project root
        try:
            video_path = str(video_file.resolve().relative_to(cwd_resolved))
        except ValueError:
            # If relative_to fails, use the path as-is (shouldn't happen in normal cases)
            video_path = str(video_file)
        choices.append((display_name, video_path))
    
    return choices




def format_generation_status(data: Dict[str, Any] | None) -> str:
    if not data:
        return "Pending"

    if data.get("ok"):
        return "✅ Complete"

    error = data.get("error")
    if error:
        return f"❌ {error}"

    return "In Progress"


def build_status_table(raw: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for block in raw.get("script", []):
        audio_status = format_generation_status(block.get("audio_generation"))
        video_status = format_generation_status(block.get("video_generation"))
        rows.append(
            {
                "ID": block.get("id", ""),
                "Character": block.get("character", ""),
                "Text": block.get("text", ""),
                "Audio": audio_status,
                "Video": video_status,
                "Status": block.get("status", ""),
            }
        )
    if not rows:
        return pd.DataFrame(columns=STATUS_COLUMNS)
    df = pd.DataFrame(rows)
    return df[STATUS_COLUMNS]


def format_project_info(raw: Dict[str, Any]) -> str:
    lines: List[str] = []
    project_name = raw.get("project", "Unknown Project")
    size = raw.get("size", "unknown")
    total_blocks = len(raw.get("script", []))
    lines.append(f"### Project Information")
    lines.append(f"- Name: `{project_name}`")
    lines.append(f"- Video Format: `{size}`")
    lines.append(f"- Text Blocks: `{total_blocks}`")

    project_status = get_project_status(raw)
    status_text = {
        ProjectStatus.CREATED: "Created",
        ProjectStatus.GENERATING: "Generating",
        ProjectStatus.GENERATE_FAILED: "Generate Failed",
        ProjectStatus.RENDERING: "Rendering",
        ProjectStatus.FINISHED: "Finished",
        ProjectStatus.FAILED: "Failed",
    }.get(project_status, "Unknown")
    
    if project_status == ProjectStatus.FAILED:
        reason = raw.get("project_failed_reason", "No reason provided")
        lines.append(f"- ⚠️ Project Status: {status_text} — {reason}")
    else:
        lines.append(f"- Project Status: {status_text}")

    return "\n".join(lines)

def get_status_text(raw: Dict[str, Any]) -> str:
    """Get status text based on project status."""
    project_status = get_project_status(raw)
    
    # Map status to text
    status_map = {
        ProjectStatus.CREATED: "Project Created",
        ProjectStatus.GENERATING: "Processing...",
        ProjectStatus.GENERATE_FAILED: "Generate Failed",
        ProjectStatus.RENDERING: "Rendering...",
        ProjectStatus.FINISHED: "Finished ✅",
        ProjectStatus.FAILED: "Failed ❌",
    }
    
    status_text = status_map.get(project_status, "Unknown Status")
    return status_text


def save_project(project_name: str, size: str, default_character: str, script_text: str, bgm_path: str, background_video_path: str, burn_subtitle: bool) -> Tuple[str, Any]:
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ Project name cannot be empty", gr.update()

    if not script_text.strip():
        return "❌ Script text cannot be empty", gr.update()

    blocks = parse_script_lines(script_text, default_character)
    if not blocks:
        return "❌ No valid script text parsed", gr.update()

    # Normalize bgm_path: empty string becomes None
    bgm_path_value = bgm_path.strip() if bgm_path.strip() else None
    # Normalize background_video_path: empty string becomes None
    background_video_path_value = background_video_path.strip() if background_video_path.strip() else None

    data = {
        "project": project_name,
        "size": size,
        "script": blocks,
        "project_status": ProjectStatus.CREATED.value,
        "bgm_path": bgm_path_value,
        "background_video": background_video_path_value,
        "burn_subtitle": burn_subtitle,  # Save subtitle burn option
    }

    project_dir = PROJECT_ROOT / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    out_path = project_dir / f"{project_name}.json"
    write_json(out_path, data)

    message = f"✅ Project `{project_name}` created: {out_path}"
    new_choices = list_projects()
    # Use gr.update() to update Dropdown component
    return message, gr.update(choices=new_choices, value=project_name)


def refresh_projects():
    new_choices = list_projects()
    # Use gr.update() to update Dropdown component
    return gr.update(choices=new_choices)


def _run_pipeline(project_name: str) -> None:
    try:
        generate_video(project_name)
    except SystemExit:
        # CLI uses SystemExit internally to terminate, just ignore it
        pass
    except Exception:
        traceback.print_exc()
    finally:
        # Mark pipeline as finished
        thread = _pipeline_threads.get(project_name)
        if thread:
            # Thread will finish naturally, we just need to mark it
            pass


def start_pipeline(project_name: str) -> Tuple[str, Any]:
    """Start pipeline and return status message and button state update."""
    if not project_name:
        return "❌ Please select a project first", gr.update()

    thread = _pipeline_threads.get(project_name)
    if thread and thread.is_alive():
        return "⚠️ Pipeline is running, please wait...", gr.update(interactive=False)

    thread = threading.Thread(target=_run_pipeline, args=(project_name,), daemon=True)
    _pipeline_threads[project_name] = thread
    thread.start()
    # Disable button while pipeline is running
    return f"🚀 Started generation pipeline for project `{project_name}`", gr.update(interactive=False)


def build_interface() -> gr.Blocks:
    character_choices = get_character_choices()
    dropdown_choices: List[Tuple[str, str]] = [("Not Set", "")] + character_choices if character_choices else [("Not Set", "")]
    bgm_choices = get_bgm_choices()
    background_video_choices = get_background_video_choices()
    project_choices = list_projects()

    with gr.Blocks(title="Videogen Console") as demo:
        selected_project_state = gr.State("")

        with gr.Tab("Create Project"):
            with gr.Row():
                project_name = gr.Textbox(label="Project Name", placeholder="e.g., yasi_demo")
                size = gr.Radio(
                    label="Video Format",
                    choices=["landscape", "tiktok"],
                    value="landscape",
                    interactive=True,
                )
            character = gr.Dropdown(
                label="Default Character",
                choices=dropdown_choices,
                value=dropdown_choices[0][1],
                allow_custom_value=True,
            )
            bgm_dropdown = gr.Dropdown(
                label="Background Music (BGM)",
                choices=bgm_choices,
                value=bgm_choices[0][1],
                allow_custom_value=False,
            )
            background_video_dropdown = gr.Dropdown(
                label="Background Video (Optional)",
                choices=background_video_choices,
                value=background_video_choices[0][1],
                allow_custom_value=False,
                info="If set, the pipeline will extract segments from this video instead of generating text-to-video. Each clip will use a sequential segment matching the audio duration.",
            )
            burn_subtitle = gr.Checkbox(
                label="Burn Subtitles to Video",
                value=True,
                info="If checked, subtitles will be hardcoded into the final video; if unchecked, subtitle burning step will be skipped",
            )
            script_input = gr.Textbox(
                label="Script Text (one line per entry, supports multiple formats)",
                placeholder="Example:\n\"huchenfeng\": This is the first sentence\nThis is the second sentence\n[L1.png:Image Title]\n\nSupported formats:\n1. Character: Text (e.g., hu: This is text)\n2. \"Character Name\": Text (e.g., \"huchenfeng\": This is text)\n3. [ImageName.png:Title] (as an image block for the previous line of text)",
                lines=10,
            )
            create_status = gr.Markdown(value="")
            create_button = gr.Button("Create Project", variant="primary")

        with gr.Tab("Project Management"):
            with gr.Row():
                project_dropdown = gr.Dropdown(
                    label="Select Project",
                    choices=project_choices,
                    value=project_choices[0] if project_choices else None,
                    allow_custom_value=False,
                )
                refresh_button = gr.Button("Refresh List")

            run_button = gr.Button("Generate Video", variant="primary")
            pipeline_status = gr.Markdown(value="")
            progress_status = gr.Markdown(value="**Status:** Waiting to start")

            with gr.Tabs():
                with gr.Tab("Progress Overview"):
                    status_table = gr.DataFrame(
                        value=pd.DataFrame(columns=STATUS_COLUMNS),
                        wrap=True,
                        interactive=False,
                    )
                with gr.Tab("Raw JSON"):
                    raw_json_view = gr.Code(language="json", value="")

        create_button.click(
            fn=save_project,
            inputs=[project_name, size, character, script_input, bgm_dropdown, background_video_dropdown, burn_subtitle],
            outputs=[create_status, project_dropdown],
        )

        refresh_button.click(fn=refresh_projects, outputs=project_dropdown)

        def load_project_with_button_state(project_name: str) -> Tuple[Any, str, str, str, Any, str]:
            """Load project and update button state based on pipeline status."""
            if not project_name:
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    "Please select a project to view details.",
                    "",
                    "",
                    gr.update(),
                    "**Status:** Waiting to start",
                )

            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ Project file not found: {json_path}",
                    "",
                    project_name,
                    gr.update(),
                    "**Status:** Project not found",
                )

            raw = read_json(json_path)
            table = build_status_table(raw)
            info = format_project_info(raw)
            raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
            
            # Check if pipeline is running for this project
            thread = _pipeline_threads.get(project_name)
            is_running = thread and thread.is_alive()
            button_update = gr.update(interactive=not is_running)
            
            # Get status text
            status_text = get_status_text(raw)
            
            return (
                table,
                info,
                raw_json,
                project_name,
                button_update,
                f"**Status:** {status_text}",
            )
        
        project_dropdown.change(
            fn=load_project_with_button_state,
            inputs=project_dropdown,
            outputs=[status_table, pipeline_status, raw_json_view, selected_project_state, run_button, progress_status],
        )

        run_button.click(
            fn=start_pipeline,
            inputs=project_dropdown,
            outputs=[pipeline_status, run_button],
        )

        def poll_project_with_button_state(project_name: str) -> Tuple[Any, str, str, Any, str]:
            """Poll project and update button state based on pipeline status."""
            if not project_name:
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    "",
                    "",
                    gr.update(),
                    "**Status:** Waiting to start",
                )

            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ Project file not found: {json_path}",
                    "",
                    gr.update(),
                    "**Status:** Project not found",
                )

            raw = read_json(json_path)
            table = build_status_table(raw)
            info = format_project_info(raw)
            raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
            
            # Check if pipeline is running for this project
            thread = _pipeline_threads.get(project_name)
            is_running = thread and thread.is_alive()
            button_update = gr.update(interactive=not is_running)
            
            # Get status text
            status_text = get_status_text(raw)
            
            return (
                table,
                info,
                raw_json,
                button_update,
                f"**Status:** {status_text}",
            )
        
        demo.load(
            fn=poll_project_with_button_state,
            inputs=selected_project_state,
            outputs=[status_table, pipeline_status, raw_json_view, run_button, progress_status],
        )

        def check_pipeline_status(project_name: str) -> Tuple[Any, str, str, Any, str]:
            """Check pipeline status and re-enable button if finished."""
            if not project_name:
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    "",
                    "",
                    gr.update(),
                    "**Status:** Waiting to start",
                )
            
            # Check if pipeline thread is still running
            thread = _pipeline_threads.get(project_name)
            is_running = thread and thread.is_alive()
            
            # Get project data
            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ Project file not found: {json_path}",
                    "",
                    gr.update(interactive=not is_running),
                    "**Status:** Project not found",
                )
            
            raw = read_json(json_path)
            table = build_status_table(raw)
            info = format_project_info(raw)
            raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
            
            # Re-enable button if pipeline is not running
            button_update = gr.update(interactive=not is_running)
            
            # Get status text
            status_text = get_status_text(raw)
            
            return (table, info, raw_json, button_update, f"**Status:** {status_text}")
        
        poll_timer = gr.Timer(value=5.0)
        poll_timer.tick(
            fn=check_pipeline_status,
            inputs=selected_project_state,
            outputs=[status_table, pipeline_status, raw_json_view, run_button, progress_status],
        )

    return demo


def main() -> None:
    demo = build_interface()
    demo.queue().launch()


if __name__ == "__main__":
    main()


