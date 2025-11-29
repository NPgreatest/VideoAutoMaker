#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr
from dataclasses import asdict
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.llm_agent.agents.auto_script import AutoScriptAgent
from videogen.llm_agent.mcp.tools.image_search.tool import ImageSearchTool
from videogen.llm_agent.utils.markdown_loader import MarkdownPromptLoader
from videogen.pipeline.parse_script import parse_script_lines
from videogen.pipeline.utils import write_json
from videogen.schema.project_schema import ProjectStatus
from videogen.ui.shared import (
    PROJECT_ROOT,
    get_background_video_choices,
    get_bgm_choices,
    get_character_choices,
)


PROMPT_LOADER = MarkdownPromptLoader()
AUTO_SCRIPT_AGENT = AutoScriptAgent()
IMAGE_SEARCH_TOOL = ImageSearchTool()
IMAGE_MARKER_PATTERN = re.compile(
    r"\[([A-Za-z0-9_.-]+):([^\]]*)\]"
)



def _get_prompt_choices(category: str, default_key: str) -> List[Tuple[str, str]]:
    registry = PROMPT_LOADER.list_registry()
    category_data = registry.get(category, {})
    if not category_data:
        return [(default_key, default_key)]
    return [
        (f"{key} · {relative_path}", key)
        for key, relative_path in category_data.items()
    ]


def _parse_image_markers(script_text: str) -> List[Tuple[str, str]]:
    markers: List[Tuple[str, str]] = []
    if not script_text:
        return markers
    for match in IMAGE_MARKER_PATTERN.finditer(script_text):
        target = match.group(1).strip()
        query = match.group(2).strip()

        markers.append((target, query))
    return markers


def _parse_image_targets(script_text: str) -> List[str]:
    return [target for target, _ in _parse_image_markers(script_text)]



def _build_image_review_data(project_name: str, script_text: str) -> List[Dict[str, Any]]:
    """
    Scan project images directory and collect main + backups for each marker.
    """

    project_dir = PROJECT_ROOT / project_name / "images"
    targets = _parse_image_targets(script_text)
    print(">>> UI checking:", project_dir, project_dir.exists())
    print(">>> DIR content:", list(project_dir.glob('*')))

    if not targets or not project_dir.exists():
        return []

    data: List[Dict[str, Any]] = []
    for target in targets:
        base = Path(target)
        stem = base.stem
        main_path = project_dir / target
        main_file = str(main_path) if main_path.exists() else None
        alt_paths = [
            str(p)
            for p in sorted(project_dir.glob(f"{stem}_*"))
            if p.is_file() and p.name != target
        ]
        data.append(
            {
                "target": target,
                "main": main_file,
                "alts": alt_paths,
            }
        )
    print("CHECK DIR:", project_dir, project_dir.exists(), list(project_dir.glob("*")))
    return data


def _dropdown_choices(targets: List[str]) -> List[Tuple[str, str]]:
    """Ensure dropdown shows full filename as label/value."""
    return [(t, t) for t in targets]


def _select_entry(entries: List[Dict[str, Any]], target: str) -> Dict[str, Any] | None:
    return next((entry for entry in entries if entry["target"] == target), None)


def _gallery_payload(entry: Dict[str, Any] | None) -> List[Any]:
    if not entry:
        return []
    payload = []
    if entry.get("main"):
        payload.append([entry["main"], f"{entry['target']} · 当前主图"])
    for alt in entry.get("alts", []):
        payload.append([alt, Path(alt).name])
    return payload


def _choice_values(entry: Dict[str, Any] | None) -> Dict[str, Any]:
    choices: List[str] = []
    if entry:
        if entry.get("main"):
            choices.append(entry["main"])
        choices.extend(entry.get("alts", []))
    return {
        "choices": choices,
        "value": choices[0] if choices else None,
    }


def refresh_image_review(project_name: str, script_text: str):
    """
    Load images for current project & script markers.
    Returns updates for dropdown, preview, gallery, picker, state, status.
    """
    project_name = (project_name or "").strip()
    data = _build_image_review_data(project_name, script_text)
    choices = [entry["target"] for entry in data]
    selected = choices[0] if choices else None
    entry = _select_entry(data, selected) if selected else None

    dropdown = gr.update(
        choices=_dropdown_choices(choices),
        value=selected,
        interactive=bool(choices),
    )
    main_image = gr.update(value=entry.get("main") if entry else None)
    gallery = gr.update(value=_gallery_payload(entry))
    picker_choices = _choice_values(entry)
    picker = gr.update(
        choices=picker_choices["choices"],
        value=picker_choices["value"],
        interactive=bool(picker_choices["choices"]),
    )
    status = (
        f"🖼️ 找到 {len(choices)} 组图片标记，可在下方选择主图并清理备份。"
        if choices
        else "ℹ️ 未检测到图片标记或项目图片目录为空。"
    )
    return dropdown, main_image, gallery, picker, data, status


def update_target_view(target: str, image_state: List[Dict[str, Any]]):
    entry = _select_entry(image_state or [], target)
    gallery = gr.update(value=_gallery_payload(entry))
    picker_choices = _choice_values(entry)
    picker = gr.update(
        choices=picker_choices["choices"],
        value=picker_choices["value"],
        interactive=bool(picker_choices["choices"]),
    )
    main_image = gr.update(value=entry.get("main") if entry else None)
    status = (
        f"正在查看 {target}，请选择正确图片后点击保存。"
        if entry
        else "未找到对应的图片，请先刷新列表。"
    )
    return main_image, gallery, picker, status


def apply_image_choice(
    project_name: str,
    script_text: str,
    target: str,
    selected_image_path: str,
):
    project_name = (project_name or "").strip()
    target = (target or "").strip()

    if not project_name or not target:
        empty = gr.update()
        return (
            empty,
            empty,
            empty,
            empty,
            [],
            "❌ 请选择项目和图片标记后再保存。",
        )

    images_dir = PROJECT_ROOT / project_name / "images"
    if not images_dir.exists():
        empty = gr.update()
        return (
            empty,
            empty,
            empty,
            empty,
            [],
            f"❌ 图片目录不存在：{images_dir}",
        )

    chosen_path = Path(selected_image_path) if selected_image_path else None
    target_path = images_dir / target
    if not chosen_path or not chosen_path.exists():
        empty = gr.update()
        return (
            empty,
            empty,
            empty,
            empty,
            [],
            "❌ 请选择要作为主图的文件。",
        )

    if chosen_path.resolve() != target_path.resolve():
        if target_path.exists():
            target_path.unlink()
        chosen_path.rename(target_path)

    stem = Path(target).stem
    cleaned = 0
    for candidate in images_dir.glob(f"{stem}_*"):
        if candidate.resolve() == target_path.resolve():
            continue
        cleaned += 1
        candidate.unlink()

    data = _build_image_review_data(project_name, script_text)
    choices = [entry["target"] for entry in data]
    dropdown = gr.update(
        choices=_dropdown_choices(choices),
        value=target,
        interactive=bool(choices),
    )
    entry = _select_entry(data, target)
    main_image = gr.update(value=entry.get("main") if entry else None)
    gallery = gr.update(value=_gallery_payload(entry))
    picker_choices = _choice_values(entry)
    picker = gr.update(
        choices=picker_choices["choices"],
        value=picker_choices["value"],
        interactive=bool(picker_choices["choices"]),
    )
    status = f"✅ 已将 {target} 的主图设为所选文件，并清理 {cleaned} 个备份。"
    return dropdown, main_image, gallery, picker, data, status



def rerun_image_search(project_name: str, script_text: str):
    """
    Re-download images by scanning script markers and running the image search tool.
    """
    project_name = (project_name or "").strip()
    script_text = script_text or ""

    if not project_name:
        dropdown, main_image, gallery, picker, data, _ = refresh_image_review(project_name, script_text)
        return dropdown, main_image, gallery, picker, data, "ℹ️ 请先填写项目名称后再重新获取图片。"

    markers = _parse_image_markers(script_text)
    if not markers:
        dropdown, main_image, gallery, picker, data, _ = refresh_image_review(project_name, script_text)
        return dropdown, main_image, gallery, picker, data, "ℹ️ 剧本中未检测到图片标记，未触发图片搜索。"

    successes = 0
    failures: List[str] = []
    for target, query in markers:
        try:
            result = IMAGE_SEARCH_TOOL.run(
                {"query": query, "project_name": project_name, "target_name": target}
            )
            if "error" in result:
                failures.append(f"{target}: {result['error']}")
            else:
                successes += 1
        except Exception as exc:  # pragma: no cover - UI 调用链路
            failures.append(f"{target}: {exc}")

    dropdown, main_image, gallery, picker, data, base_status = refresh_image_review(project_name, script_text)

    parts = [f"🖼️ 已重新获取 {successes}/{len(markers)} 组图片。"]
    if failures:
        tail = " ..." if len(failures) > 3 else ""
        parts.append("⚠️ 失败: " + "; ".join(failures[:3]) + tail)
    parts.append(base_status)
    status = "\n\n".join(parts)
    return dropdown, main_image, gallery, picker, data, status


def generate_script_from_agent(
    topic: str,
    size: str,
    default_character: str,
    info_query_key: str,
    script_structure_key: str,
    project_name: str,
) -> Tuple[Any, str]:
    topic = (topic or "").strip()
    if not topic:
        return gr.update(), "❌ 视频主题不能为空"

    style = (default_character or "").strip() or "通用风格"
    # 如果没有提供 project_name，使用 topic（视频主题）作为 project_name
    project_name = (project_name or "").strip() or topic

    try:
        result = AUTO_SCRIPT_AGENT.run(
            topic=topic,
            style=style,
            prompt1_key=info_query_key or AutoScriptAgent.PROMPT_1_DEFAULT_KEY,
            prompt2_key=script_structure_key or AutoScriptAgent.PROMPT_2_DEFAULT_KEY,
            project_name=project_name,
        )
    except Exception as exc:  # pragma: no cover - UI 调用链路
        return gr.update(), f"❌ 生成剧本失败：{exc}"

    return result.final_script, "✅ 剧本已自动生成，可直接微调后创建项目。"


def _save_project_assets(
    project_name: str,
    size: str,
    default_character: str,
    global_context: str,
    show_character_overlay: bool,
    script_text: str,
    bgm_path: str,
    background_video_path: str,
    burn_subtitle: bool,
    blocks: list,
) -> str:
    project_dir = PROJECT_ROOT / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    script_dicts = [asdict(block) for block in blocks]

    project_payload = {
        "project_name": project_name,
        "size": size,
        "script": script_dicts,
        "project_status": ProjectStatus.CREATED.value,
        "global_context": global_context or None,
        "show_character_overlay": bool(show_character_overlay),
        "bgm_path": bgm_path or None,
        "background_video": background_video_path or None,
        "burn_subtitle": burn_subtitle,
    }
    project_json_path = project_dir / f"{project_name}.json"
    write_json(project_json_path, project_payload)
    return str(project_json_path)


def _reset_project_blocks(project_name: str) -> None:
    dao = WorkingBlockDAO()
    existing = dao.get_all(project_name)
    for wb in existing:
        dao.delete(wb.id)


def create_project(
    project_name: str,
    size: str,
    default_character: str,
    video_topic: str,
    global_context: str,
    show_character_overlay: bool,
    script_text: str,
    bgm_path: str,
    background_video_path: str,
    burn_subtitle: bool,
) -> str:
    project_name = (project_name or "").strip()
    if not project_name:
        return "❌ Project name cannot be empty"
    if not video_topic or not video_topic.strip():
        return "❌ Video topic cannot be empty"
    if not script_text or not script_text.strip():
        return "❌ Script text cannot be empty"

    blocks = parse_script_lines(
        script_text,
        default_character,
        size,
        background_video_path or None,
        show_character_overlay,
    )
    if not blocks:
        return "❌ No valid script lines parsed."

    _reset_project_blocks(project_name)
    project_json_path = _save_project_assets(
        project_name,
        size,
        default_character,
        global_context,
        show_character_overlay,
        script_text,
        bgm_path.strip(),
        background_video_path.strip(),
        burn_subtitle,
        blocks,
    )

    message = (
        f"✅ 项目 `{project_name}` 已创建。\n\n"
        f"- project JSON: `{project_json_path}`"
    )
    return message


def build_create_project_page() -> None:
    character_choices = get_character_choices()
    default_character_value = character_choices[0][1] if character_choices else ""
    bgm_choices = get_bgm_choices()
    background_video_choices = get_background_video_choices()
    info_query_choices = _get_prompt_choices(
        AutoScriptAgent.PROMPT_1_CATEGORY, AutoScriptAgent.PROMPT_1_DEFAULT_KEY
    )
    script_structure_choices = _get_prompt_choices(
        AutoScriptAgent.PROMPT_2_CATEGORY, AutoScriptAgent.PROMPT_2_DEFAULT_KEY
    )

    with gr.Column():
        gr.Markdown("### 🆕 Create Project\n为项目输入名称和脚本，系统会自动解析为脚本块并初始化数据库。")
        project_name = gr.Textbox(label="Project Name", placeholder="e.g., tech_demo", max_lines=1, value="", interactive=True)
        video_topic = gr.Textbox(
            label="Video Topic",
            placeholder="例如：为什么 B+ 树在数据库里无处不在？",
            max_lines=1,
        )
        global_context = gr.Textbox(
            label="Global Context",
            placeholder="例如：整体风格、背景设定、目标受众等全局信息",
            lines=2,
        )
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
        with gr.Row():
            info_query_prompt = gr.Dropdown(
                label="Info Query Prompt",
                choices=info_query_choices,
                value=info_query_choices[0][1] if info_query_choices else "",
            )
            script_structure_prompt = gr.Dropdown(
                label="Script Structure Prompt",
                choices=script_structure_choices,
                value=script_structure_choices[0][1]
                if script_structure_choices
                else "",
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
        show_character_overlay = gr.Checkbox(
            label="显示角色人像（Character Overlay）",
            value=True,
        )
        script_text = gr.Textbox(
            label="Script Text",
            placeholder='"character": your line\nnext line...',
            lines=12,
        )
        with gr.Accordion("🖼️ 图片核对与备份清理", open=False):
            image_status = gr.Markdown("生成剧本后会自动展示图片及备选项。")
            with gr.Row():
                image_target_dropdown = gr.Dropdown(
                    label="图片标记",
                    choices=[],
                    interactive=True,
                )
                refresh_images_btn = gr.Button("刷新图片列表", variant="secondary")
                regrab_images_btn = gr.Button("重新获取图片", variant="secondary")
            main_image_preview = gr.Image(
                label="当前主图",
                type="filepath",
                interactive=False,
            )
            image_gallery = gr.Gallery(
                label="主图 + 备选",
                columns=4,
                height=320,
                allow_preview=True,
            )
            image_choice_radio = gr.Radio(
                label="请选择正确的图片并点击保存",
                choices=[],
                interactive=True,
            )
            apply_image_btn = gr.Button("保存选择并清理备份", variant="primary")
            image_state = gr.State([])
        status = gr.Markdown("")
        generate_btn = gr.Button("Generate Script", variant="secondary")
        create_btn = gr.Button("Create Project", variant="primary")

    generate_btn.click(
        fn=generate_script_from_agent,
        inputs=[
            video_topic,
            size,
            default_character,
            info_query_prompt,
            script_structure_prompt,
            project_name,
        ],
        outputs=[script_text, status],
    ).then(
        fn=refresh_image_review,
        inputs=[project_name, script_text],
        outputs=[
            image_target_dropdown,
            main_image_preview,
            image_gallery,
            image_choice_radio,
            image_state,
            image_status,
        ],
    )
    create_btn.click(
        fn=create_project,
        inputs=[
            project_name,
            size,
            default_character,
            video_topic,
            global_context,
            show_character_overlay,
            script_text,
            bgm_dropdown,
            background_video_dropdown,
            burn_subtitle,
        ],
        outputs=[status],
    )

    refresh_images_btn.click(
        fn=refresh_image_review,
        inputs=[project_name, script_text],
        outputs=[
            image_target_dropdown,
            main_image_preview,
            image_gallery,
            image_choice_radio,
            image_state,
            image_status,
        ],
    )

    regrab_images_btn.click(
        fn=rerun_image_search,
        inputs=[project_name, script_text],
        outputs=[
            image_target_dropdown,
            main_image_preview,
            image_gallery,
            image_choice_radio,
            image_state,
            image_status,
        ],
    )

    image_target_dropdown.change(
        fn=update_target_view,
        inputs=[image_target_dropdown, image_state],
        outputs=[main_image_preview, image_gallery, image_choice_radio, image_status],
    )

    apply_image_btn.click(
        fn=apply_image_choice,
        inputs=[
            project_name,
            script_text,
            image_target_dropdown,
            image_choice_radio,
        ],
        outputs=[
            image_target_dropdown,
            main_image_preview,
            image_gallery,
            image_choice_radio,
            image_state,
            image_status,
        ],
    )
