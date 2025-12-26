#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from wiki2video.cli.core_project_builder import build_project_from_script
from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.llm_agent.mcp.tools.image_search.tool import ImageSearchTool
from wiki2video.llm_engine.markdown_loader import MarkdownPromptLoader
from wiki2video.ui.shared import (
    PROJECT_ROOT,
    get_background_video_choices,
    get_bgm_choices,
)

# NEW orchestrator
from wiki2video.llm_agent.agents.wiki2video import Wiki2VideoInteractiveOrchestrator
orchestrator = Wiki2VideoInteractiveOrchestrator()

PROMPT_LOADER = MarkdownPromptLoader()
IMAGE_SEARCH_TOOL = ImageSearchTool()
IMAGE_MARKER_PATTERN = re.compile(r"\[([A-Za-z0-9_.-]+):([^\]]*)\]")


# ============================================================
# Helper Functions
# ============================================================

def _parse_image_markers(script_text: str) -> List[Tuple[str, str]]:
    markers = []
    if not script_text:
        return markers
    for m in IMAGE_MARKER_PATTERN.finditer(script_text):
        markers.append((m.group(1), m.group(2)))
    return markers


def _parse_image_targets(script_text: str) -> List[str]:
    return [name for name, _ in _parse_image_markers(script_text)]


def _build_image_review_data(project_id: str, script_text: str):
    images_dir = PROJECT_ROOT / project_id / "images"
    targets = _parse_image_targets(script_text)

    if not images_dir.exists() or not targets:
        return []

    data = []
    for target in targets:
        base = Path(target)
        stem = base.stem

        main_path = images_dir / target
        main = str(main_path) if main_path.exists() else None

        alts = [
            str(p) for p in sorted(images_dir.glob(f"{stem}_*"))
            if p.is_file() and p.name != target
        ]

        data.append({"target": target, "main": main, "alts": alts})
    return data


def _dropdown_choices(targets: List[str]):
    return [(t, t) for t in targets]


def _gallery_payload(entry):
    if not entry:
        return []
    payload = []
    if entry.get("main"):
        payload.append([entry["main"], f"{entry['target']} · 主图"])
    for alt in entry.get("alts", []):
        payload.append([alt, Path(alt).name])
    return payload


def refresh_image_review(project_id: str, script_text: str):
    data = _build_image_review_data(project_id, script_text)
    targets = [d["target"] for d in data]

    if not data:
        return (
            gr.update(choices=[], value=None, interactive=False),
            gr.update(value=None),
            gr.update(value=[]),
            gr.update(choices=[], value=None),
            [],
            "ℹ️ 未检测到图片标记或未找到项目图片目录。",
        )

    first = data[0]
    return (
        gr.update(choices=_dropdown_choices(targets), value=targets[0], interactive=True),
        gr.update(value=first["main"]),
        gr.update(value=_gallery_payload(first)),
        gr.update(choices=[first["main"]] + first["alts"], value=first["main"]),
        data,
        f"🖼️ 找到 {len(targets)} 组图片，您可以审查主图与备选项。",
    )


def update_target_view(target: str, image_state: List[Dict[str, Any]]):
    entry = next((e for e in image_state if e["target"] == target), None)
    if not entry:
        return gr.update(), gr.update(), gr.update(), "未找到图片标记"

    choices = [entry["main"]] + entry["alts"]
    return (
        gr.update(value=entry["main"]),
        gr.update(value=_gallery_payload(entry)),
        gr.update(choices=choices, value=choices[0]),
        f"正在查看 {target} 的图片，请选择主图",
    )


def apply_image_choice(project_id: str, script_text: str, target: str, selected_img: str):
    if not project_id or not target or not selected_img:
        return gr.update(), gr.update(), gr.update(), gr.update(), [], "❌ 缺少必要参数"

    images_dir = PROJECT_ROOT / project_id / "images"
    tgt_path = images_dir / target
    selected_path = Path(selected_img)

    if tgt_path.exists():
        tgt_path.unlink()
    selected_path.rename(tgt_path)

    for f in images_dir.glob(f"{Path(target).stem}_*"):
        if f.name != target:
            f.unlink()

    return refresh_image_review(project_id, script_text)


def rerun_image_search(project_id: str, script_text: str):
    markers = _parse_image_markers(script_text)
    if not markers:
        return refresh_image_review(project_id, script_text)

    ok = 0
    for target, q in markers:
        res = IMAGE_SEARCH_TOOL.run(
            {"query": q, "project_name": project_id, "target_name": target}
        )
        if "error" not in res:
            ok += 1

    base = refresh_image_review(project_id, script_text)
    return (*base[:-1], f"🖼️ 重新获取成功 {ok}/{len(markers)} 组\n" + base[-1])


# ============================================================
# Save Project
# ============================================================

def _reset_project_blocks(project_id: str):
    dao = WorkingBlockDAO()
    for wb in dao.get_all(project_id):
        dao.delete(wb.id)


# ============================================================
# UI Wrapper for build_project (fix argument mismatch)
# ============================================================
def build_project_ui(
    project_id,
    size,
    global_context,
    show_character_overlay,
    script_text,
    bgm_path,
    bg_video_path,
    burn_subtitle,
):
    """
    UI wrapper: maps UI inputs into the exact keyword-only arguments
    required by build_project().
    """
    try:
        # ⚠ 关键：严格按照错误提示中的 keyword-only 参数传入
        result = build_project_from_script(
            script_text,
            project_id,
            size=size,
            global_context=global_context,
            show_overlay=show_character_overlay,
            bgm=bgm_path,
            bg_video=bg_video_path,
            burn=burn_subtitle,
        )

        return f"✅ 项目创建成功：{project_id}\n\n{result}"

    except Exception as e:
        return f"❌ 创建项目失败：{e}"


# ============================================================
# Main UI
# ============================================================

def build_create_project_page():
    bgm_choices = get_bgm_choices()
    bg_video_choices = get_background_video_choices()

    with gr.Column():
        gr.Markdown("# 🆕 Wiki → Video Project Builder")

        project_id = gr.Textbox(
            label="Project ID (Required)",
            placeholder="例如：mohenjo_demo",
        )

        # Step 1
        gr.Markdown("## Step 1 — 输入 Wikipedia 地址")

        wiki_input = gr.Textbox(
            label="Wikipedia URL / Topic",
            placeholder="例如：https://en.wikipedia.org/wiki/Mohenjo-daro",
        )

        fetch_btn = gr.Button("🎬 从 Wiki 自动生成完整剧本（含插图）")

        script_text = gr.Textbox(label="Generated Script", lines=14)

        global_context = gr.Textbox(label="Global Context", lines=3)

        # Step 2 — Image Review
        with gr.Accordion("🖼️ 图片审查", open=False):
            image_status = gr.Markdown("等待剧本…")
            image_target_dropdown = gr.Dropdown(
                label="图片标记",
                choices=[],
                value=None,
                interactive=False,
            )
            refresh_images_btn = gr.Button("刷新图片列表")
            regrab_images_btn = gr.Button("重新获取图片")
            main_image_preview = gr.Image(label="当前主图", type="filepath")
            image_gallery = gr.Gallery(label="主图 + 备选", columns=4, height=250)
            image_choice_radio = gr.Radio(label="主图选择", choices=[])
            apply_image_btn = gr.Button("保存主图", variant="primary")
            image_state = gr.State([])

        # Step 3 — Settings
        gr.Markdown("## Step 3 — 项目设置")

        size = gr.Radio(
            label="Video Format",
            choices=["landscape", "tiktok"],
            value="tiktok",
        )
        bgm_dropdown = gr.Dropdown(label="Background Music", choices=bgm_choices)
        bg_video_dropdown = gr.Dropdown(label="Background Video", choices=bg_video_choices)
        burn_subtitle = gr.Checkbox(label="Burn Subtitles", value=True)
        show_character_overlay = gr.Checkbox(label="显示角色人像", value=True)

        create_btn = gr.Button("📁 创建项目")
        status = gr.Markdown("")

    # ============================================================
    # Bind Events
    # ============================================================

    async def _run_full_pipeline(url, pname):
        if not pname.strip():
            return "❌ 请先填写 Project ID", ""

        script, gctx = await orchestrator.run_full(url, pname)
        return script, gctx

    # small wrapper so refresh_image only receives script
    def _after_script_fetched(script, gctx):
        return script

    # ---- RUN (script + global_context) ----
    fetch_btn.click(
        _run_full_pipeline,
        inputs=[wiki_input, project_id],
        outputs=[script_text, global_context],   # AUTO FILL CONTEXT
    ).then(
        _after_script_fetched,
        inputs=[script_text, global_context],
        outputs=[script_text],
    ).then(
        refresh_image_review,
        inputs=[project_id, script_text],
        outputs=[
            image_target_dropdown,
            main_image_preview,
            image_gallery,
            image_choice_radio,
            image_state,
            image_status,
        ],
    )

    # ---- Image Review Buttons ----
    refresh_images_btn.click(
        refresh_image_review,
        inputs=[project_id, script_text],
        outputs=[
            image_target_dropdown, main_image_preview, image_gallery,
            image_choice_radio, image_state, image_status
        ],
    )

    regrab_images_btn.click(
        rerun_image_search,
        inputs=[project_id, script_text],
        outputs=[
            image_target_dropdown, main_image_preview, image_gallery,
            image_choice_radio, image_state, image_status
        ],
    )

    image_target_dropdown.change(
        update_target_view,
        inputs=[image_target_dropdown, image_state],
        outputs=[main_image_preview, image_gallery, image_choice_radio, image_status],
    )

    apply_image_btn.click(
        apply_image_choice,
        inputs=[project_id, script_text, image_target_dropdown, image_choice_radio],
        outputs=[
            image_target_dropdown, main_image_preview, image_gallery,
            image_choice_radio, image_state, image_status
        ],
    )

    # ---- Create Project ----
    create_btn.click(
        build_project_ui,
        inputs=[
            project_id,
            size,
            global_context,
            show_character_overlay,
            script_text,
            bgm_dropdown,
            bg_video_dropdown,
            burn_subtitle,
        ],
        outputs=[status],
    )
