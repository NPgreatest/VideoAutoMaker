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
STATUS_COLUMNS = ["编号", "角色", "文本", "音频", "视频", "状态"]


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
    choices: List[Tuple[str, str]] = [("不使用 BGM", "")]
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




def format_generation_status(data: Dict[str, Any] | None) -> str:
    if not data:
        return "待处理"

    if data.get("ok"):
        return "✅ 完成"

    error = data.get("error")
    if error:
        return f"❌ {error}"

    return "进行中"


def build_status_table(raw: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for block in raw.get("script", []):
        audio_status = format_generation_status(block.get("audio_generation"))
        video_status = format_generation_status(block.get("video_generation"))
        rows.append(
            {
                "编号": block.get("id", ""),
                "角色": block.get("character", ""),
                "文本": block.get("text", ""),
                "音频": audio_status,
                "视频": video_status,
                "状态": block.get("status", ""),
            }
        )
    if not rows:
        return pd.DataFrame(columns=STATUS_COLUMNS)
    df = pd.DataFrame(rows)
    return df[STATUS_COLUMNS]


def format_project_info(raw: Dict[str, Any]) -> str:
    lines: List[str] = []
    project_name = raw.get("project", "未知项目")
    size = raw.get("size", "unknown")
    total_blocks = len(raw.get("script", []))
    lines.append(f"### 项目信息")
    lines.append(f"- 名称：`{project_name}`")
    lines.append(f"- 视频格式：`{size}`")
    lines.append(f"- 文本段落：`{total_blocks}`")

    project_status = get_project_status(raw)
    status_text = {
        ProjectStatus.CREATED: "已创建",
        ProjectStatus.GENERATING: "生成中",
        ProjectStatus.GENERATE_FAILED: "生成失败",
        ProjectStatus.RENDERING: "渲染中",
        ProjectStatus.FINISHED: "已完成",
        ProjectStatus.FAILED: "失败",
    }.get(project_status, "未知")
    
    if project_status == ProjectStatus.FAILED:
        reason = raw.get("project_failed_reason", "未提供原因")
        lines.append(f"- ⚠️ 项目状态：{status_text} — {reason}")
    else:
        lines.append(f"- 项目状态：{status_text}")

    return "\n".join(lines)

def get_status_text(raw: Dict[str, Any]) -> str:
    """Get status text based on project status."""
    project_status = get_project_status(raw)
    
    # Map status to text
    status_map = {
        ProjectStatus.CREATED: "项目已创建",
        ProjectStatus.GENERATING: "处理中...",
        ProjectStatus.GENERATE_FAILED: "生成失败",
        ProjectStatus.RENDERING: "渲染中...",
        ProjectStatus.FINISHED: "已完成 ✅",
        ProjectStatus.FAILED: "失败 ❌",
    }
    
    status_text = status_map.get(project_status, "未知状态")
    return status_text


def save_project(project_name: str, size: str, default_character: str, script_text: str, bgm_path: str, burn_subtitle: bool) -> Tuple[str, Any]:
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ 项目名不能为空", gr.update()

    if not script_text.strip():
        return "❌ 剧本文本不能为空", gr.update()

    blocks = parse_script_lines(script_text, default_character)
    if not blocks:
        return "❌ 未解析到有效的剧本文本", gr.update()

    # Normalize bgm_path: empty string becomes None
    bgm_path_value = bgm_path.strip() if bgm_path.strip() else None

    data = {
        "project": project_name,
        "size": size,
        "script": blocks,
        "project_status": ProjectStatus.CREATED.value,
        "bgm_path": bgm_path_value,
        "burn_subtitle": burn_subtitle,  # Save subtitle burn option
    }

    project_dir = PROJECT_ROOT / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    out_path = project_dir / f"{project_name}.json"
    write_json(out_path, data)

    message = f"✅ 项目 `{project_name}` 已创建：{out_path}"
    new_choices = list_projects()
    # 使用 gr.update() 更新 Dropdown 组件
    return message, gr.update(choices=new_choices, value=project_name)


def refresh_projects():
    new_choices = list_projects()
    # 使用 gr.update() 更新 Dropdown 组件
    return gr.update(choices=new_choices)


def _run_pipeline(project_name: str) -> None:
    try:
        generate_video(project_name)
    except SystemExit:
        # CLI 内部使用 SystemExit 终止，忽略即可
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
        return "❌ 请先选择项目", gr.update()

    thread = _pipeline_threads.get(project_name)
    if thread and thread.is_alive():
        return "⚠️ 管线正在运行，请稍候...", gr.update(interactive=False)

    thread = threading.Thread(target=_run_pipeline, args=(project_name,), daemon=True)
    _pipeline_threads[project_name] = thread
    thread.start()
    # Disable button while pipeline is running
    return f"🚀 已启动项目 `{project_name}` 的生成流程", gr.update(interactive=False)


def build_interface() -> gr.Blocks:
    character_choices = get_character_choices()
    dropdown_choices: List[Tuple[str, str]] = [("不设置", "")] + character_choices if character_choices else [("不设置", "")]
    bgm_choices = get_bgm_choices()
    project_choices = list_projects()

    with gr.Blocks(title="Videogen 控制台") as demo:
        selected_project_state = gr.State("")

        with gr.Tab("创建项目"):
            with gr.Row():
                project_name = gr.Textbox(label="项目名称", placeholder="例如：yasi_demo")
                size = gr.Radio(
                    label="视频格式",
                    choices=["landscape", "tiktok"],
                    value="landscape",
                    interactive=True,
                )
            character = gr.Dropdown(
                label="默认角色",
                choices=dropdown_choices,
                value=dropdown_choices[0][1],
                allow_custom_value=True,
            )
            bgm_dropdown = gr.Dropdown(
                label="背景音乐 (BGM)",
                choices=bgm_choices,
                value=bgm_choices[0][1],
                allow_custom_value=False,
            )
            burn_subtitle = gr.Checkbox(
                label="烧录字幕到视频",
                value=True,
                info="如果勾选，字幕将硬编码到最终视频中；如果不勾选，将跳过字幕烧录步骤",
            )
            script_input = gr.Textbox(
                label="剧本文本（每行一条，支持多种格式）",
                placeholder="示例：\n\"huchenfeng\": 这是第一句\n这是第二句\n[L1.png:图片标题]\n\n支持的格式：\n1. 角色: 文本（如：hu: 这是文本）\n2. \"角色名\": 文本（如：\"huchenfeng\": 这是文本）\n3. [图片名.png:标题]（作为前一行文本的图片块）",
                lines=10,
            )
            create_status = gr.Markdown(value="")
            create_button = gr.Button("创建项目", variant="primary")

        with gr.Tab("项目管理"):
            with gr.Row():
                project_dropdown = gr.Dropdown(
                    label="选择项目",
                    choices=project_choices,
                    value=project_choices[0] if project_choices else None,
                    allow_custom_value=False,
                )
                refresh_button = gr.Button("刷新列表")

            run_button = gr.Button("生成成片", variant="primary")
            pipeline_status = gr.Markdown(value="")
            progress_status = gr.Markdown(value="**状态：** 等待开始")

            with gr.Tabs():
                with gr.Tab("进度概览"):
                    status_table = gr.DataFrame(
                        value=pd.DataFrame(columns=STATUS_COLUMNS),
                        wrap=True,
                        interactive=False,
                    )
                with gr.Tab("原始 JSON"):
                    raw_json_view = gr.Code(language="json", value="")

        create_button.click(
            fn=save_project,
            inputs=[project_name, size, character, script_input, bgm_dropdown, burn_subtitle],
            outputs=[create_status, project_dropdown],
        )

        refresh_button.click(fn=refresh_projects, outputs=project_dropdown)

        def load_project_with_button_state(project_name: str) -> Tuple[Any, str, str, str, Any, str]:
            """Load project and update button state based on pipeline status."""
            if not project_name:
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    "请选择项目查看详情。",
                    "",
                    "",
                    gr.update(),
                    "**状态：** 等待开始",
                )

            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ 未找到项目文件：{json_path}",
                    "",
                    project_name,
                    gr.update(),
                    "**状态：** 未找到项目",
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
                f"**状态：** {status_text}",
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
                    "**状态：** 等待开始",
                )

            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ 未找到项目文件：{json_path}",
                    "",
                    gr.update(),
                    "**状态：** 未找到项目",
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
                f"**状态：** {status_text}",
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
                    "**状态：** 等待开始",
                )
            
            # Check if pipeline thread is still running
            thread = _pipeline_threads.get(project_name)
            is_running = thread and thread.is_alive()
            
            # Get project data
            json_path = PROJECT_ROOT / project_name / f"{project_name}.json"
            if not json_path.exists():
                return (
                    pd.DataFrame(columns=STATUS_COLUMNS),
                    f"❌ 未找到项目文件：{json_path}",
                    "",
                    gr.update(interactive=not is_running),
                    "**状态：** 未找到项目",
                )
            
            raw = read_json(json_path)
            table = build_status_table(raw)
            info = format_project_info(raw)
            raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
            
            # Re-enable button if pipeline is not running
            button_update = gr.update(interactive=not is_running)
            
            # Get status text
            status_text = get_status_text(raw)
            
            return (table, info, raw_json, button_update, f"**状态：** {status_text}")
        
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


