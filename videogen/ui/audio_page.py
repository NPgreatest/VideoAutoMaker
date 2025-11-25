#!/usr/bin/env python3
from __future__ import annotations

import json
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

# ----------------------------------------
# Fix Windows/mac paths → POSIX
# ----------------------------------------
def sanitize_path(p: str) -> str:
    if not p:
        return ""
    try:
        p = p.strip().strip('"').strip("'")
        p = Path(p).expanduser().resolve()
        return p.as_posix()
    except:
        return p.replace("\\", "/")


# ----------------------------------------
# Collect audio info
# ----------------------------------------
def _collect_audio_data(project_name: str):
    """Return df, banner, audio list, dropdown list"""
    if not project_name:
        return pd.DataFrame(columns=AUDIO_TABLE_COLUMNS), "请选择项目", [], [], False

    raw = load_project_raw(project_name)
    if not raw:
        return pd.DataFrame(columns=AUDIO_TABLE_COLUMNS), f"❌ 未找到项目 {project_name}", [], [], False

    dao = WorkingBlockDAO()
    audio_blocks = {
        (wb.block_id or wb.id): wb
        for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio"
    }

    rows = []
    dropdown = []
    audio_items = []
    all_ready = True

    for block in raw["script"]:
        block_id = block["id"]
        text = block["text"]

        audio_action = next(
            (a for a in block["actions"] if a.get("type") == "fish_audio"),
            {}
        )
        character = audio_action.get("config", {}).get("character", "")

        dropdown.append((f"{block_id} · {character}", block_id))

        wb = audio_blocks.get(block_id)
        status = "⏳ 待生成"
        duration = ""
        output_path = ""

        if wb:
            try:
                r = json.loads(wb.result_json or "{}")
            except:
                r = {}

            output_path = r.get("output_path") or wb.output_path or ""
            if r.get("duration_sec"):
                duration = f"{float(r['duration_sec']):.2f}"

            if wb.status == WorkingBlockStatus.SUCCESS:
                status = "✅ 成功"
            elif wb.status == WorkingBlockStatus.ERROR:
                status = "❌ 失败"
                all_ready = False
            elif wb.status == WorkingBlockStatus.PENDING:
                status = "⏳ 待生成"
                all_ready = False
            else:
                status = "⚙️ 运行中"
                all_ready = False
        else:
            all_ready = False

        rows.append({
            "Block ID": block_id,
            "Character": character,
            "Text": format_text_preview(text),
            "Duration(s)": duration or "—",
            "状态": status,
            "输出文件": output_path or "—",
        })

        if output_path and Path(output_path).exists():
            audio_items.append({
                "path": sanitize_path(output_path),
                "label": f"{block_id} · {character} ({duration}s)" if duration else block_id,
            })

    df = pd.DataFrame(rows)
    banner = "🎉 Audio Ready!" if all_ready else "🔈 检查音频"

    return df, banner, audio_items, dropdown, all_ready


# ----------------------------------------
# Pagination helper
# ----------------------------------------
ITEMS_PER_PAGE = 2


def _paginate_audio(audio_items: List[Dict], page: int):
    total = len(audio_items)
    max_page = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    page = max(1, min(page, max_page))

    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = audio_items[start:end]

    return page_items, page, max_page


# ----------------------------------------
# Update UI
# ----------------------------------------
def _update_audio_panel(project_name: str, page: int, audio_slots: int):
    df, banner, audio_items, dropdown, _ = _collect_audio_data(project_name)

    page_items, page, max_page = _paginate_audio(audio_items, page)

    updates = []

    # Fill EXACT audio slots count
    for i in range(audio_slots):
        if i < len(page_items):
            it = page_items[i]
            updates.append(gr.update(value=it["path"], visible=True, label=it["label"]))
        else:
            updates.append(gr.update(value=None, visible=False))

    return (
        df,
        banner,
        page,
        max_page,
        *updates,
        gr.update(choices=dropdown, value=None),
        gr.update(interactive=not is_pipeline_running(project_name)),
    )


# ----------------------------------------
# Pipeline actions
# ----------------------------------------
def start_audio_pipeline(project_name: str):
    if not project_name:
        return "❌ 请选择项目", gr.update()

    json_path = project_json_path(project_name)
    if not json_path.exists():
        return f"❌ 项目不存在 {project_name}", gr.update()

    ok = launch_pipeline_thread(project_name, lambda: run_audio_pipeline(json_path))
    if not ok:
        return "⚙️ pipeline 正在运行", gr.update(interactive=False)

    return f"🚀 开始运行 {project_name} 音频 pipeline", gr.update(interactive=False)


def retry_audio_block(project_name: str, block_id: str):
    if not block_id:
        return "❌ 请选择脚本块", gr.update()

    dao = WorkingBlockDAO()
    blocks = [
        wb for wb in dao.get_all(project_name)
        if wb.method_name == "fish_audio" and (wb.block_id or wb.id) == block_id
    ]

    if not blocks:
        return f"⚠️ {block_id} 找不到音频块", gr.update(value=None)

    for wb in blocks:
        wb.status = WorkingBlockStatus.PENDING
        wb.output_path = None
        wb.result_json = ""
        dao.update(wb)

    return f"🔁 已重置 {block_id}", gr.update(value=None)


# ----------------------------------------
# Build UI Page
# ----------------------------------------
def build_audio_page() -> None:
    project_choices = list_projects()

    # Estimate max blocks for allocating fixed audio components
    max_blocks = 0
    for p in project_choices:
        raw = load_project_raw(p)
        if raw:
            max_blocks = max(max_blocks, len(raw.get("script", [])))

    audio_slots = ITEMS_PER_PAGE  # 10 per page

    with gr.Column():
        gr.Markdown("### 🎙️ Audio Pipeline")

        with gr.Row():
            audio_project = gr.Dropdown(choices=project_choices, label="选择项目")
            audio_refresh = gr.Button("刷新")

        audio_banner = gr.Markdown("")
        audio_table = gr.DataFrame(interactive=False, wrap=True)

        # ------------- Pagination UI -------------
        with gr.Row():
            page_state = gr.Number(value=1, interactive=False, label="页码")
            max_page_state = gr.Number(value=1, interactive=False, label="总页数")
        with gr.Row():
            prev_btn = gr.Button("⬅ 上一页")
            next_btn = gr.Button("➡ 下一页")

        # ------------- Audio players (10 slots) -------------
        audio_players = [
            gr.Audio(label=f"Audio {i+1}", type="filepath", visible=False)
            for i in range(audio_slots)
        ]


        with gr.Row():
            gen_btn = gr.Button("Generate Audio", variant="primary")
            retry_dropdown = gr.Dropdown(label="选择重试块")
            retry_btn = gr.Button("Retry")

        action_msg = gr.Markdown("")

    audio_refresh.click(lambda: gr.update(choices=list_projects()), outputs=audio_project)

    outputs = [
        audio_table, audio_banner, page_state, max_page_state,
        *audio_players, retry_dropdown, gen_btn
    ]

    audio_project.change(
        fn=lambda p: _update_audio_panel(p, 1, audio_slots),
        inputs=audio_project,
        outputs=outputs,
    )

    prev_btn.click(
        fn=lambda p, cur: _update_audio_panel(p, cur - 1, audio_slots),
        inputs=[audio_project, page_state],
        outputs=outputs,
    )

    next_btn.click(
        fn=lambda p, cur: _update_audio_panel(p, cur + 1, audio_slots),
        inputs=[audio_project, page_state],
        outputs=outputs,
    )

    gen_btn.click(
        fn=start_audio_pipeline,
        inputs=audio_project,
        outputs=[action_msg, gen_btn],
    ).then(
        fn=lambda p: _update_audio_panel(p, 1, audio_slots),
        inputs=audio_project,
        outputs=outputs,
    )

    retry_btn.click(
        fn=retry_audio_block,
        inputs=[audio_project, retry_dropdown],
        outputs=[action_msg, retry_dropdown],
    ).then(
        fn=lambda p: _update_audio_panel(p, 1, audio_slots),
        inputs=audio_project,
        outputs=outputs,
    )

    # Timer 仅刷新表格 + banner + 页码（安全）
    audio_timer = gr.Timer(value=AUDIO_POLL_SECONDS)
    audio_timer.tick(
        fn=lambda p: _update_audio_panel(p, page_state.value, audio_slots)[:4],
        inputs=audio_project,
        outputs=[audio_table, audio_banner, page_state, max_page_state],
    )
