#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr
from dataclasses import asdict
from typing import Any, Dict, Tuple

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.parse_script import parse_script_lines
from videogen.pipeline.utils import write_json
from videogen.schema.project_schema import ProjectStatus
from videogen.ui.shared import (
    PROJECT_ROOT,
    get_background_video_choices,
    get_bgm_choices,
    get_character_choices,
)


def _save_project_assets(
    project_name: str,
    size: str,
    default_character: str,
    script_text: str,
    bgm_path: str,
    background_video_path: str,
    burn_subtitle: bool,
    blocks: list,
) -> Tuple[str, str]:
    project_dir = PROJECT_ROOT / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    raw_payload: Dict[str, Any] = {
        "project_name": project_name,
        "size": size,
        "default_character": default_character,
        "script_text": script_text,
        "bgm_path": bgm_path or "",
        "background_video": background_video_path or "",
        "burn_subtitle": burn_subtitle,
    }
    raw_path = project_dir / "raw.json"
    write_json(raw_path, raw_payload)

    script_dicts = [asdict(block) for block in blocks]

    project_payload = {
        "project_name": project_name,
        "size": size,
        "script": script_dicts,
        "project_status": ProjectStatus.CREATED.value,
        "bgm_path": bgm_path or None,
        "background_video": background_video_path or None,
        "burn_subtitle": burn_subtitle,
    }
    project_json_path = project_dir / f"{project_name}.json"
    write_json(project_json_path, project_payload)
    return str(raw_path), str(project_json_path)


def _reset_project_blocks(project_name: str) -> None:
    dao = WorkingBlockDAO()
    existing = dao.get_all(project_name)
    for wb in existing:
        dao.delete(wb.id)


def create_project(
    project_name: str,
    size: str,
    default_character: str,
    script_text: str,
    bgm_path: str,
    background_video_path: str,
    burn_subtitle: bool,
) -> str:
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ Project name cannot be empty"
    if not script_text or not script_text.strip():
        return "❌ Script text cannot be empty"

    blocks = parse_script_lines(script_text, default_character, size, background_video_path or None)
    if not blocks:
        return "❌ No valid script lines parsed."

    _reset_project_blocks(project_name)
    raw_path, project_json_path = _save_project_assets(
        project_name,
        size,
        default_character,
        script_text,
        bgm_path.strip(),
        background_video_path.strip(),
        burn_subtitle,
        blocks,
    )

    message = (
        f"✅ 项目 `{project_name}` 已创建。\n\n"
        f"- raw.json: `{raw_path}`\n"
        f"- project JSON: `{project_json_path}`"
    )
    return message


def build_create_project_page() -> None:
    character_choices = get_character_choices()
    default_character_value = character_choices[0][1] if character_choices else ""
    bgm_choices = get_bgm_choices()
    background_video_choices = get_background_video_choices()

    with gr.Column():
        gr.Markdown("### 🆕 Create Project\n为项目输入名称和脚本，系统会自动解析为脚本块并初始化数据库。")
        project_name = gr.Textbox(label="Project Name", placeholder="e.g., tech_demo", max_lines=1)
        with gr.Row():
            size = gr.Radio(
                label="Video Format",
                choices=["landscape", "tiktok"],
                value="tiktok",
            )
            default_character = gr.Dropdown(
                label="Default Character",
                choices=character_choices or [("Not Set", "")],
                value=default_character_value,
                allow_custom_value=True,
            )
        bgm_dropdown = gr.Dropdown(
            label="Background Music (BGM)",
            choices=bgm_choices,
            value=bgm_choices[0][1] if bgm_choices else "",
        )
        background_video_dropdown = gr.Dropdown(
            label="Background Video",
            choices=background_video_choices,
            value=background_video_choices[0][1] if background_video_choices else "",
        )
        burn_subtitle = gr.Checkbox(label="Burn Subtitles to Final Video", value=True)
        script_text = gr.Textbox(
            label="Script Text",
            placeholder='"character": your line\nnext line...',
            lines=12,
        )
        status = gr.Markdown("")
        create_btn = gr.Button("Create Project", variant="primary")

    create_btn.click(
        fn=create_project,
        inputs=[
            project_name,
            size,
            default_character,
            script_text,
            bgm_dropdown,
            background_video_dropdown,
            burn_subtitle,
        ],
        outputs=[status],
    )


