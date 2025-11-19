#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import mimetypes
import threading
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd

from videogen.cli.generate import generate_audio, generate_video
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.parse_script import parse_script_lines
from videogen.pipeline.utils import (
    get_project_status,
    load_character_config,
    read_json,
    write_json,
)
from videogen.pipeline.working_block import WorkingBlockStatus
from videogen.schema.project_schema import ProjectStatus

PROJECT_ROOT = Path("project")
BGM_ROOT = Path("assets/bgm")
BACKGROUND_VIDEO_ROOT = Path("assets/background_videos")
AUDIO_TABLE_COLUMNS = ["Block ID", "Text", "Audio 状态", "输出文件"]
VIDEO_TABLE_COLUMNS = ["Block ID", "Method", "状态", "输出文件"]
POLL_SECONDS = 4.0

_pipeline_threads: Dict[str, threading.Thread] = {}


# ---------------------------------------------------------------------------
# Project & asset helpers
# ---------------------------------------------------------------------------
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


def _project_json_path(project_name: str) -> Path:
    return PROJECT_ROOT / project_name / f"{project_name}.json"


def _load_project_raw(project_name: str) -> Optional[Dict[str, Any]]:
    if not project_name:
        return None
    json_path = _project_json_path(project_name)
    if not json_path.exists():
        return None
    return read_json(json_path)


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
    choices: List[Tuple[str, str]] = [("No BGM", "")]
    if not BGM_ROOT.exists():
        return choices

    cwd_resolved = Path.cwd().resolve()
    for bgm_file in sorted(BGM_ROOT.glob("*.wav")):
        display_name = bgm_file.stem
        try:
            bgm_path = str(bgm_file.resolve().relative_to(cwd_resolved))
        except ValueError:
            bgm_path = str(bgm_file)
        choices.append((display_name, bgm_path))
    return choices


def get_background_video_choices() -> List[Tuple[str, str]]:
    choices: List[Tuple[str, str]] = [("No Background Video", "")]
    if not BACKGROUND_VIDEO_ROOT.exists():
        return choices

    cwd_resolved = Path.cwd().resolve()
    video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"]
    video_files: List[Path] = []
    for ext in video_extensions:
        video_files.extend(BACKGROUND_VIDEO_ROOT.glob(ext))

    for video_file in sorted(video_files):
        display_name = video_file.stem
        try:
            video_path = str(video_file.resolve().relative_to(cwd_resolved))
        except ValueError:
            video_path = str(video_file)
        choices.append((display_name, video_path))
    return choices


# ---------------------------------------------------------------------------
# Create project
# ---------------------------------------------------------------------------
def save_project(
    project_name: str,
    size: str,
    default_character: str,
    script_text: str,
    bgm_path: str,
    background_video_path: str,
    burn_subtitle: bool,
) -> Tuple[str, Any]:
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ Project name cannot be empty", gr.update()

    if not script_text.strip():
        return "❌ Script text cannot be empty", gr.update()

    blocks = parse_script_lines(script_text, default_character, size, background_video_path)
    if not blocks:
        return "❌ No valid script text parsed", gr.update()

    bgm_path_value = bgm_path.strip() if bgm_path.strip() else None
    background_video_value = background_video_path.strip() if background_video_path.strip() else None
    script_dicts = [asdict(block) for block in blocks]

    data = {
        "project_name": project_name,
        "size": size,
        "script": script_dicts,
        "project_status": ProjectStatus.CREATED.value,
        "bgm_path": bgm_path_value,
        "background_video": background_video_value,
        "burn_subtitle": burn_subtitle,
    }

    project_dir = PROJECT_ROOT / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    out_path = project_dir / f"{project_name}.json"
    write_json(out_path, data)

    message = f"✅ Project `{project_name}` created: {out_path}"
    new_choices = list_projects()
    return message, gr.update(choices=new_choices, value=project_name)


def refresh_projects() -> Any:
    return gr.update(choices=list_projects())


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def _format_text_preview(text: str, limit: int = 36) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _extract_output_path(wb) -> str:
    if not wb or not wb.result_json:
        return ""
    try:
        result = json.loads(wb.result_json)
        return result.get("output_path") or ""
    except Exception:
        return ""


def _encode_audio_player(block_id: str, output_path: str) -> Optional[str]:
    if not output_path:
        return None
    path = Path(output_path)
    if not path.exists():
        return None
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "audio/wav"
    try:
        data = path.read_bytes()
    except Exception:
        return None
    encoded = base64.b64encode(data).decode("utf-8")
    return (
        f"<div style='margin-bottom:12px'>"
        f"<strong>{block_id}</strong><br/>"
        f"<audio controls src='data:{mime};base64,{encoded}' style='width:100%'></audio>"
        f"</div>"
    )


def _get_audio_dashboard(project_name: str) -> Tuple[pd.DataFrame, str, str, List[Tuple[str, str]], bool]:
    if not project_name:
        return (
            pd.DataFrame(columns=AUDIO_TABLE_COLUMNS),
            "请选择项目以查看音频状态。",
            "暂无音频可播放",
            [],
            False,
        )

    raw = _load_project_raw(project_name)
    if not raw:
        return (
            pd.DataFrame(columns=AUDIO_TABLE_COLUMNS),
            f"❌ 未找到项目：{project_name}",
            "暂无音频可播放",
            [],
            False,
        )

    dao = WorkingBlockDAO()
    audio_blocks = {
        (wb.block_id or wb.id): wb
        for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio"
    }

    rows: List[Dict[str, str]] = []
    html_players: List[str] = []
    block_choices: List[Tuple[str, str]] = []
    all_ready = True

    for block in raw.get("script", []):
        block_id = block.get("id", "")
        text_preview = _format_text_preview(block.get("text", ""))
        block_choices.append((f"{block_id} · {text_preview}", block_id))

        wb = audio_blocks.get(block_id)
        output_path = _extract_output_path(wb)

        if wb is None:
            status_label = "⏳ 待生成"
            all_ready = False
        elif wb.status == WorkingBlockStatus.SUCCESS:
            status_label = "✅ 成功"
        elif wb.status == WorkingBlockStatus.ERROR:
            status_label = "❌ 失败"
            all_ready = False
        else:
            status_label = "⚙️ 运行中"
            all_ready = False

        rows.append(
            {
                "Block ID": block_id,
                "Text": text_preview,
                "Audio 状态": status_label,
                "输出文件": output_path or "—",
            }
        )

        player_html = _encode_audio_player(block_id, output_path)
        if player_html:
            html_players.append(player_html)

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=AUDIO_TABLE_COLUMNS)
    banner = (
        "🎉 Audio Ready! 可以进入视频阶段了。"
        if all_ready and rows
        else "🔈 请生成或检查所有音频。"
    )
    players_html = "".join(html_players) or "暂无音频可播放"
    return df, banner, players_html, block_choices, all_ready


def retry_audio_block(project_name: str, block_id: str) -> Tuple[str, Any]:
    if not project_name:
        return "❌ 请先选择项目。", gr.update()
    if not block_id:
        return "❌ 请先选择需要重试的脚本块。", gr.update()

    dao = WorkingBlockDAO()
    target_blocks = [
        wb
        for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio" and wb.block_id == block_id
    ]

    if not target_blocks:
        return f"⚠️ 找不到脚本块 {block_id} 的音频任务。", gr.update()

    for wb in target_blocks:
        wb.status = WorkingBlockStatus.PENDING
        wb.result_json = ""
        wb.output_path = None
        dao.update(wb)

    return f"🔁 已重置 {block_id}，再次点击“Generate Audio”即可重试。", gr.update(value=None)


# ---------------------------------------------------------------------------
# Video helpers
# ---------------------------------------------------------------------------
def _get_video_dashboard(project_name: str) -> Tuple[pd.DataFrame, str, Any]:
    if not project_name:
        return (
            pd.DataFrame(columns=VIDEO_TABLE_COLUMNS),
            "请选择项目以查看视频状态。",
            gr.update(value=None),
        )

    raw = _load_project_raw(project_name)
    if not raw:
        return (
            pd.DataFrame(columns=VIDEO_TABLE_COLUMNS),
            f"❌ 未找到项目：{project_name}",
            gr.update(value=None),
        )

    dao = WorkingBlockDAO()
    video_blocks = [
        wb for wb in dao.get_all(project_name) if wb.method_name != "fish_audio"
    ]

    rows: List[Dict[str, str]] = []
    final_video_path: Optional[str] = None

    for wb in video_blocks:
        output_path = _extract_output_path(wb)
        if wb.method_name == "concat" and wb.status == WorkingBlockStatus.SUCCESS and output_path:
            final_video_path = output_path

        if wb.status == WorkingBlockStatus.SUCCESS:
            status_label = "✅ 成功"
        elif wb.status == WorkingBlockStatus.ERROR:
            status_label = "❌ 失败"
        else:
            status_label = "⚙️ 运行中"

        rows.append(
            {
                "Block ID": wb.block_id or wb.id,
                "Method": wb.method_name,
                "状态": status_label,
                "输出文件": output_path or "—",
            }
        )

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=VIDEO_TABLE_COLUMNS)
    project_status = get_project_status(raw)
    status_map = {
        ProjectStatus.CREATED: "项目刚创建，需先完成音频阶段。",
        ProjectStatus.AUDIO_GENERATING: "音频生成中……",
        ProjectStatus.AUDIO_READY: "Audio Ready！可以开始视频阶段。",
        ProjectStatus.VIDEO_GENERATING: "视频生成中……",
        ProjectStatus.FINISHED: "🎬 视频已完成！",
        ProjectStatus.FAILED: "❌ 项目失败，请检查日志。",
    }
    status_text = status_map.get(project_status, "状态未知")
    video_update = gr.update(value=final_video_path) if final_video_path else gr.update(value=None)
    return df, status_text, video_update


# ---------------------------------------------------------------------------
# Thread management
# ---------------------------------------------------------------------------
def _is_thread_running(project_name: str) -> bool:
    thread = _pipeline_threads.get(project_name)
    return bool(thread and thread.is_alive())


def _run_audio_worker(project_name: str) -> None:
    try:
        generate_audio(project_name)
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()


def _run_video_worker(project_name: str) -> None:
    try:
        generate_video(project_name)
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()


def start_audio_pipeline(project_name: str) -> Tuple[str, Any]:
    if not project_name:
        return "❌ 请先选择项目。", gr.update()

    raw = _load_project_raw(project_name)
    if not raw:
        return f"❌ 未找到项目：{project_name}", gr.update()

    status = get_project_status(raw)
    if status in (ProjectStatus.VIDEO_GENERATING, ProjectStatus.FINISHED):
        return "⚠️ 视频阶段已开始或完成，无法再编辑音频。", gr.update()

    if _is_thread_running(project_name):
        return "⚙️ 当前已有任务在运行，请稍候。", gr.update(interactive=False)

    thread = threading.Thread(target=_run_audio_worker, args=(project_name,), daemon=True)
    _pipeline_threads[project_name] = thread
    thread.start()
    return f"🚀 已启动 `{project_name}` 的音频阶段。", gr.update(interactive=False)


def start_video_pipeline(project_name: str) -> Tuple[str, Any]:
    if not project_name:
        return "❌ 请先选择项目。", gr.update()

    raw = _load_project_raw(project_name)
    if not raw:
        return f"❌ 未找到项目：{project_name}", gr.update()

    status = get_project_status(raw)
    if status != ProjectStatus.AUDIO_READY:
        return "⚠️ 需要先完成所有音频 (Audio Ready)。", gr.update(interactive=False)

    if _is_thread_running(project_name):
        return "⚙️ 当前已有任务在运行，请稍候。", gr.update(interactive=False)

    thread = threading.Thread(target=_run_video_worker, args=(project_name,), daemon=True)
    _pipeline_threads[project_name] = thread
    thread.start()
    return f"🎬 已启动 `{project_name}` 的视频阶段。", gr.update(interactive=False)


# ---------------------------------------------------------------------------
# UI builders
# ---------------------------------------------------------------------------
def _update_audio_panel(project_name: str) -> Tuple[Any, str, Any, Any, Any]:
    df, banner, html_players, block_choices, _ = _get_audio_dashboard(project_name)
    button_state = gr.update(interactive=not _is_thread_running(project_name))
    dropdown_update = gr.update(choices=block_choices, value=None)
    return df, banner, gr.update(value=html_players), dropdown_update, button_state


def _update_video_panel(project_name: str) -> Tuple[Any, str, Any, Any]:
    df, status_text, video_update = _get_video_dashboard(project_name)
    raw = _load_project_raw(project_name)
    status = get_project_status(raw) if raw else ProjectStatus.CREATED
    allow_video = (
        status == ProjectStatus.AUDIO_READY and not _is_thread_running(project_name)
    )
    button_state = gr.update(interactive=allow_video)
    return df, status_text, video_update, button_state


def build_interface() -> gr.Blocks:
    character_choices = get_character_choices()
    dropdown_choices: List[Tuple[str, str]] = (
        [("Not Set", "")] + character_choices if character_choices else [("Not Set", "")]
    )
    bgm_choices = get_bgm_choices()
    background_video_choices = get_background_video_choices()
    project_choices = list_projects()

    with gr.Blocks(title="Videogen Console") as demo:
        # -------------------------- Tab 1: Create Project --------------------------
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
                info="如果设置，则直接使用该视频拆段作为背景。",
            )
            burn_subtitle = gr.Checkbox(
                label="Burn Subtitles to Video",
                value=True,
                info="勾选后会把字幕压进最终视频。",
            )
            script_input = gr.Textbox(
                label="Script Text",
                placeholder="示例：\n\"huchenfeng\": 第一段台词\n第二段台词\n…",
                lines=10,
            )
            create_status = gr.Markdown(value="")
            create_button = gr.Button("Create Project", variant="primary")

        # -------------------------- Tab 2: Audio Pipeline --------------------------
        with gr.Tab("Audio Pipeline"):
            with gr.Row():
                audio_project = gr.Dropdown(
                    label="选择项目",
                    choices=project_choices,
                    value=project_choices[0] if project_choices else None,
                    allow_custom_value=False,
                )
                audio_refresh = gr.Button("刷新项目列表")

            audio_banner = gr.Markdown("请选择项目以开始音频阶段。")
            audio_table = gr.DataFrame(
                value=pd.DataFrame(columns=AUDIO_TABLE_COLUMNS),
                interactive=False,
                wrap=True,
            )
            audio_players = gr.HTML("暂无音频可播放")

            with gr.Row():
                generate_audio_btn = gr.Button("Generate Audio", variant="primary")
                retry_block_dropdown = gr.Dropdown(
                    label="选择需要重试的脚本块",
                    choices=[],
                    allow_custom_value=False,
                )
                retry_button = gr.Button("Retry Audio")

            audio_action_msg = gr.Markdown("")

        # -------------------------- Tab 3: Video Pipeline --------------------------
        with gr.Tab("Video Pipeline"):
            with gr.Row():
                video_project = gr.Dropdown(
                    label="选择项目",
                    choices=project_choices,
                    value=project_choices[0] if project_choices else None,
                    allow_custom_value=False,
                )
                video_refresh = gr.Button("刷新项目列表")

            video_status = gr.Markdown("Audio Ready 之后才能执行视频阶段。")
            video_table = gr.DataFrame(
                value=pd.DataFrame(columns=VIDEO_TABLE_COLUMNS),
                interactive=False,
                wrap=True,
            )
            final_video_view = gr.Video(label="最终视频预览", value=None)
            generate_video_btn = gr.Button("Generate Video", variant="primary")
            video_action_msg = gr.Markdown("")

        # -------------------------- Wiring --------------------------
        create_button.click(
            fn=save_project,
            inputs=[
                project_name,
                size,
                character,
                script_input,
                bgm_dropdown,
                background_video_dropdown,
                burn_subtitle,
            ],
            outputs=[create_status, audio_project],
        ).then(
            fn=refresh_projects,
            outputs=video_project,
        )

        audio_refresh.click(fn=refresh_projects, outputs=audio_project)
        video_refresh.click(fn=refresh_projects, outputs=video_project)

        audio_project.change(
            fn=_update_audio_panel,
            inputs=audio_project,
            outputs=[audio_table, audio_banner, audio_players, retry_block_dropdown, generate_audio_btn],
        )

        video_project.change(
            fn=_update_video_panel,
            inputs=video_project,
            outputs=[video_table, video_status, final_video_view, generate_video_btn],
        )

        generate_audio_btn.click(
            fn=start_audio_pipeline,
            inputs=audio_project,
            outputs=[audio_action_msg, generate_audio_btn],
        ).then(
            fn=_update_audio_panel,
            inputs=audio_project,
            outputs=[audio_table, audio_banner, audio_players, retry_block_dropdown, generate_audio_btn],
        )

        retry_button.click(
            fn=retry_audio_block,
            inputs=[audio_project, retry_block_dropdown],
            outputs=[audio_action_msg, retry_block_dropdown],
        ).then(
            fn=_update_audio_panel,
            inputs=audio_project,
            outputs=[audio_table, audio_banner, audio_players, retry_block_dropdown, generate_audio_btn],
        )

        generate_video_btn.click(
            fn=start_video_pipeline,
            inputs=video_project,
            outputs=[video_action_msg, generate_video_btn],
        ).then(
            fn=_update_video_panel,
            inputs=video_project,
            outputs=[video_table, video_status, final_video_view, generate_video_btn],
        )

        audio_timer = gr.Timer(value=POLL_SECONDS)
        audio_timer.tick(
            fn=_update_audio_panel,
            inputs=audio_project,
            outputs=[audio_table, audio_banner, audio_players, retry_block_dropdown, generate_audio_btn],
        )

        video_timer = gr.Timer(value=POLL_SECONDS)
        video_timer.tick(
            fn=_update_video_panel,
            inputs=video_project,
            outputs=[video_table, video_status, final_video_view, generate_video_btn],
        )

    return demo


def main() -> None:
    demo = build_interface()
    demo.queue().launch()


if __name__ == "__main__":
    main()

