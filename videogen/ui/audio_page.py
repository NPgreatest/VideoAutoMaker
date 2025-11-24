#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
import pandas as pd

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.pipeline import run_audio_pipeline
from videogen.pipeline.working_block import WorkingBlockStatus
from videogen.ui.shared import (
    AUDIO_POLL_SECONDS,
    AUDIO_TABLE_COLUMNS,
    format_text_preview,
    is_pipeline_running,
    launch_pipeline_thread,
    list_projects,
    load_project_raw,
    project_json_path,
)

AUDIO_PLAYERS_COUNT = 0


def _parse_result_json(wb) -> Dict[str, Any]:
    try:
        if wb.result_json:
            data = json.loads(wb.result_json)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _format_duration(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        duration = float(value)
        if duration <= 0:
            return ""
        return f"{duration:.2f}"
    except (TypeError, ValueError):
        return ""


def _collect_audio_dashboard(project_name: str):
    if not project_name:
        empty_df = pd.DataFrame(columns=AUDIO_TABLE_COLUMNS)
        return empty_df, "请选择项目以查看音频状态。", [], [], False

    raw = load_project_raw(project_name)
    if not raw:
        empty_df = pd.DataFrame(columns=AUDIO_TABLE_COLUMNS)
        return empty_df, f"❌ 未找到项目：{project_name}", [], [], False

    dao = WorkingBlockDAO()
    audio_blocks = {
        (wb.block_id or wb.id): wb
        for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio"
    }

    rows: List[Dict[str, Any]] = []
    dropdown_choices: List[Tuple[str, str]] = []
    player_payloads: List[Dict[str, str]] = []
    all_ready = True

    for block in raw.get("script", []):
        block_id = block.get("id") or ""
        block_text = block.get("text") or ""
        audio_action = next(
            (action for action in block.get("actions", []) if action.get("type") == "fish_audio"),
            {},
        )
        character = audio_action.get("config", {}).get("character") if isinstance(audio_action, dict) else ""
        dropdown_choices.append((f"{block_id} · {character or '未设置'}", block_id))

        wb = audio_blocks.get(block_id)
        status_label = "⏳ 待生成"
        duration_label = ""
        output_path = ""

        if wb:
            result = _parse_result_json(wb)
            output_path = result.get("output_path") or wb.output_path or ""
            duration_label = _format_duration(result.get("duration_sec"))

            if wb.status == WorkingBlockStatus.SUCCESS:
                status_label = "✅ 成功"
            elif wb.status == WorkingBlockStatus.ERROR:
                status_label = "❌ 失败"
                all_ready = False
            elif wb.status == WorkingBlockStatus.PENDING:
                status_label = "⏳ 待生成"
                all_ready = False
            else:
                status_label = "⚙️ 运行中"
                all_ready = False
        else:
            all_ready = False

        rows.append(
            {
                "Block ID": block_id,
                "Character": character or "—",
                "Text": format_text_preview(block_text),
                "Duration(s)": duration_label or "—",
                "状态": status_label,
                "输出文件": output_path or "—",
            }
        )

        if output_path and Path(output_path).exists():
            player_payloads.append(
                {
                    "path": output_path,
                    "block_id": block_id,
                    "character": character or "未设置",
                    "duration": duration_label or "未知",
                }
            )

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=AUDIO_TABLE_COLUMNS)
    banner = "🎉 Audio Ready! 可以进入视频阶段了。" if all_ready and rows else "🔈 请生成或检查所有音频。"
    return df, banner, player_payloads, dropdown_choices, all_ready


def _refresh_dropdown():
    return gr.update(choices=list_projects())


def _update_audio_panel(project_name: str):
    df, banner, player_payloads, dropdown_choices, _ = _collect_audio_dashboard(project_name)
    player_updates: List[gr.Update] = []
    for idx in range(AUDIO_PLAYERS_COUNT):
        if idx < len(player_payloads):
            payload = player_payloads[idx]
            label = f"{payload['block_id']} · {payload['character']} ({payload['duration']}s)"
            player_updates.append(
                gr.update(value=payload["path"], label=label, visible=True)
            )
        else:
            player_updates.append(gr.update(value=None, visible=False))
    dropdown_update = gr.update(choices=dropdown_choices, value=None)
    button_state = gr.update(interactive=not is_pipeline_running(project_name))
    return (df, banner, *player_updates, dropdown_update, button_state)


def start_audio_pipeline(project_name: str):
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ 请先选择项目。", gr.update()

    json_path = project_json_path(project_name)
    if not json_path.exists():
        return f"❌ 未找到项目：{project_name}", gr.update()

    def _runner():
        run_audio_pipeline(json_path)

    started = launch_pipeline_thread(project_name, _runner)
    if not started:
        return "⚙️ 当前已有任务在运行，请稍候。", gr.update(interactive=False)

    return f"🚀 已启动 `{project_name}` 的音频阶段。", gr.update(interactive=False)


def retry_audio_block(project_name: str, block_id: str):
    if not project_name:
        return "❌ 请先选择项目。", gr.update()
    if not block_id:
        return "❌ 请先选择需要重试的脚本块。", gr.update()

    dao = WorkingBlockDAO()
    target_blocks = [
        wb
        for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio" and (wb.block_id or wb.id) == block_id
    ]
    if not target_blocks:
        return f"⚠️ 找不到脚本块 {block_id} 的音频任务。", gr.update(value=None)

    for wb in target_blocks:
        wb.status = WorkingBlockStatus.PENDING
        wb.output_path = None
        wb.result_json = ""
        dao.update(wb)

    return f"🔁 已重置 {block_id}，再次点击“Generate Audio”即可重试。", gr.update(value=None)


def _calc_max_audio_players() -> int:
    max_blocks = 0
    for project_name in list_projects():
        raw = load_project_raw(project_name)
        if raw and isinstance(raw.get("script"), list):
            max_blocks = max(max_blocks, len(raw["script"]))
    # Provide some headroom for new projects; ensure multiples of 4 for layout
    max_blocks = max(8, max_blocks + 8)
    rows = math.ceil(max_blocks / 4)
    return rows * 4


def build_audio_page() -> None:
    global AUDIO_PLAYERS_COUNT
    project_choices = list_projects()
    empty_df = pd.DataFrame(columns=AUDIO_TABLE_COLUMNS)
    AUDIO_PLAYERS_COUNT = _calc_max_audio_players()

    with gr.Column():
        gr.Markdown("### 🎙️ Audio Pipeline\n运行 fish_audio 任务并查看每个脚本块的生成状态。")
        with gr.Row():
            audio_project = gr.Dropdown(
                label="选择项目",
                choices=project_choices,
                value=project_choices[0] if project_choices else None,
            )
            audio_refresh = gr.Button("刷新项目列表")

        audio_banner = gr.Markdown("请选择项目以开始音频阶段。")
        audio_table = gr.DataFrame(
            value=empty_df,
            interactive=False,
            wrap=True,
        )
        gr.Markdown("#### 音频预览")
        audio_players: List[gr.Audio] = []
        rows = AUDIO_PLAYERS_COUNT // 4
        for row_idx in range(rows):
            with gr.Row():
                for col_idx in range(4):
                    idx = row_idx * 4 + col_idx
                    audio_players.append(
                        gr.Audio(
                            label=f"Audio Preview {idx + 1}",
                            interactive=False,
                            type="filepath",
                            visible=False,
                        )
                    )

        with gr.Row():
            generate_audio_btn = gr.Button("Generate Audio", variant="primary")
            retry_block_dropdown = gr.Dropdown(
                label="选择需要重试的脚本块",
                choices=[],
                allow_custom_value=False,
            )
            retry_button = gr.Button("Retry Audio")

        audio_action_msg = gr.Markdown("")

    audio_refresh.click(fn=_refresh_dropdown, outputs=audio_project)

    audio_outputs = [audio_table, audio_banner, *audio_players, retry_block_dropdown, generate_audio_btn]

    audio_project.change(
        fn=_update_audio_panel,
        inputs=audio_project,
        outputs=audio_outputs,
    )

    generate_audio_btn.click(
        fn=start_audio_pipeline,
        inputs=audio_project,
        outputs=[audio_action_msg, generate_audio_btn],
    ).then(
        fn=_update_audio_panel,
        inputs=audio_project,
        outputs=audio_outputs,
    )

    retry_button.click(
        fn=retry_audio_block,
        inputs=[audio_project, retry_block_dropdown],
        outputs=[audio_action_msg, retry_block_dropdown],
    ).then(
        fn=_update_audio_panel,
        inputs=audio_project,
        outputs=audio_outputs,
    )

    audio_timer = gr.Timer(value=AUDIO_POLL_SECONDS)
    audio_timer.tick(
        fn=_update_audio_panel,
        inputs=audio_project,
        outputs=audio_outputs,
    )


