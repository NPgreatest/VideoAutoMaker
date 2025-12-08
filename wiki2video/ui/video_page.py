#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
import pandas as pd

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.core.pipeline import run_video_pipeline
from wiki2video.core.utils import get_project_status
from wiki2video.core.working_block import WorkingBlockStatus
from wiki2video.schema.project_schema import ProjectStatus
from wiki2video.ui.shared import (
    PROJECT_ROOT,
    VIDEO_POLL_SECONDS,
    VIDEO_TABLE_COLUMNS,
    is_pipeline_running,
    launch_pipeline_thread,
    list_projects,
    load_project_raw,
    project_json_path,
)


STATUS_TEXT = {
    ProjectStatus.CREATED: "项目刚创建，需先完成音频阶段。",
    ProjectStatus.AUDIO_GENERATING: "音频生成中……",
    ProjectStatus.AUDIO_READY: "Audio Ready！可以开始视频阶段。",
    ProjectStatus.VIDEO_GENERATING: "视频生成中……",
    ProjectStatus.FINISHED: "🎬 视频已完成！",
    ProjectStatus.FAILED: "❌ 项目失败，请检查日志。",
}


def _parse_result_json(wb) -> Dict[str, Any]:
    try:
        if wb.result_json:
            data = json.loads(wb.result_json)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _collect_video_dashboard(project_id: str):
    if not project_id:
        empty_df = pd.DataFrame(columns=VIDEO_TABLE_COLUMNS)
        return empty_df, "请选择项目以查看视频状态。", [], None

    raw = load_project_raw(project_id)
    if not raw:
        empty_df = pd.DataFrame(columns=VIDEO_TABLE_COLUMNS)
        return empty_df, f"❌ 未找到项目：{project_id}", [], None

    dao = WorkingBlockDAO()
    video_blocks = [
        wb for wb in dao.get_all(project_id) if wb.method_name != "text_audio"
    ]

    rows: List[Dict[str, Any]] = []
    dropdown_choices: List[Tuple[str, str]] = []
    final_video_path = PROJECT_ROOT / project_id / f"{project_id}.mp4"
    final_video_value = str(final_video_path) if final_video_path.exists() else None

    for wb in video_blocks:
        result = _parse_result_json(wb)
        output_path = result.get("output_path") or wb.output_path or ""
        readable_status = "⚙️ 运行中"
        if wb.status == WorkingBlockStatus.SUCCESS:
            readable_status = "✅ 成功"
        elif wb.status == WorkingBlockStatus.ERROR:
            readable_status = "❌ 失败"

        rows.append(
            {
                "Block ID": wb.block_id or wb.id,
                "Method": wb.method_name,
                "状态": readable_status,
                "输出文件": output_path or "—",
            }
        )

        dropdown_choices.append(
            (f"{wb.block_id or wb.id} · {wb.method_name}", wb.id)
        )

        if (
            wb.method_name == "concat"
            and wb.status == WorkingBlockStatus.SUCCESS
            and output_path
            and Path(output_path).exists()
        ):
            final_video_value = output_path

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=VIDEO_TABLE_COLUMNS)
    status = get_project_status(raw)
    return df, STATUS_TEXT.get(status, "状态未知"), dropdown_choices, final_video_value


def _refresh_dropdown():
    return gr.update(choices=list_projects())


def _update_video_panel(project_id: str):
    df, status_text, dropdown_choices, video_value = _collect_video_dashboard(project_id)
    dropdown_update = gr.update(choices=dropdown_choices, value=None)
    video_update = gr.update(value=video_value)
    button_state = gr.update(interactive=not is_pipeline_running(project_id))
    return df, status_text, video_update, dropdown_update, button_state


def start_video_pipeline(project_id: str):
    project_id = (project_id or "").strip()
    if not project_id:
        return "❌ 请先选择项目。", gr.update()

    json_path = project_json_path(project_id)
    if not json_path.exists():
        return f"❌ 未找到项目：{project_id}", gr.update()

    raw = load_project_raw(project_id)
    if not raw:
        return f"❌ 未找到项目：{project_id}", gr.update()

    def _runner():
        run_video_pipeline(project_id)

    started = launch_pipeline_thread(project_id, _runner)
    if not started:
        return "⚙️ 当前已有任务在运行，请稍候。", gr.update(interactive=False)

    return f"🎬 已启动 `{project_id}` 的视频阶段。", gr.update(interactive=False)


def retry_video_block(project_id: str, working_block_id: str):
    if not project_id:
        return "❌ 请先选择项目。", gr.update()
    if not working_block_id:
        return "❌ 请先选择需要重试的工作块。", gr.update(value=None)

    dao = WorkingBlockDAO()
    wb = dao.get_by_id(working_block_id)
    if not wb or wb.method_name == "text_audio":
        return "⚠️ 未找到对应的视频任务。", gr.update(value=None)

    wb.status = WorkingBlockStatus.PENDING
    wb.output_path = None
    wb.result_json = ""
    dao.update(wb)
    return f"🔁 已重置 {wb.block_id or wb.id} · {wb.method_name}。", gr.update(value=None)


def build_video_page() -> None:
    project_choices = list_projects()
    empty_df = pd.DataFrame(columns=VIDEO_TABLE_COLUMNS)

    with gr.Column():
        gr.Markdown("### 🎬 Video Pipeline\n当 Audio Ready 后，运行视频阶段并查看整体进度。")
        with gr.Row():
            video_project = gr.Dropdown(
                label="选择项目",
                choices=project_choices,
                value=project_choices[0] if project_choices else None,
            )
            video_refresh = gr.Button("刷新项目列表")

        video_status = gr.Markdown("Audio Ready 之后才能执行视频阶段。")
        video_table = gr.DataFrame(value=empty_df, interactive=False, wrap=True)
        final_video_view = gr.Video(label="最终视频预览", value=None)

        with gr.Row():
            generate_video_btn = gr.Button("Generate Video", variant="primary")
            video_retry_dropdown = gr.Dropdown(
                label="选择需要重试的工作块",
                choices=[],
                value=None,
                allow_custom_value=False,
            )
            retry_button = gr.Button("Retry Video Block")

        video_action_msg = gr.Markdown("")

    video_refresh.click(fn=_refresh_dropdown, outputs=video_project)

    video_project.change(
        fn=_update_video_panel,
        inputs=video_project,
        outputs=[video_table, video_status, final_video_view, video_retry_dropdown, generate_video_btn],
    )

    generate_video_btn.click(
        fn=start_video_pipeline,
        inputs=video_project,
        outputs=[video_action_msg, generate_video_btn],
    ).then(
        fn=_update_video_panel,
        inputs=video_project,
        outputs=[video_table, video_status, final_video_view, video_retry_dropdown, generate_video_btn],
    )

    retry_button.click(
        fn=retry_video_block,
        inputs=[video_project, video_retry_dropdown],
        outputs=[video_action_msg, video_retry_dropdown],
    ).then(
        fn=_update_video_panel,
        inputs=video_project,
        outputs=[video_table, video_status, final_video_view, video_retry_dropdown, generate_video_btn],
    )

    video_timer = gr.Timer(value=VIDEO_POLL_SECONDS)
    video_timer.tick(
        fn=_update_video_panel,
        inputs=video_project,
        outputs=[video_table, video_status, final_video_view, video_retry_dropdown, generate_video_btn],
    )
