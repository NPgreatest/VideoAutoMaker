#!/usr/bin/env python3
"""
Ultra-simplified Script parsing:
ScriptBlock + ActionSpec[] with NO ids, NO prev_ids.
Pipeline will auto-generate ids & dependencies.
"""

from typing import Any, Dict, List
import re

from videogen.schema.action_spec import ActionSpec
from videogen.schema.project_schema import ScriptBlock


def parse_script_lines(
    script_text: str,
    default_character: str,
    size: str = "tiktok",
    background_video: str = None,
) -> List[ScriptBlock]:

    script_blocks: List[ScriptBlock] = []
    if not script_text:
        return script_blocks

    line_index = 1
    lines = script_text.splitlines()

    # 👇 新增：用于判断角色变化
    prev_character = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # ------------------------------------------------
        # 1. Picture-only line: [img.png:title]
        # ------------------------------------------------
        picture_match = re.match(r'^\[([^:]+):(.*)\]$', line)
        if picture_match:
            picture_filename = picture_match.group(1).strip()
            picture_title = picture_match.group(2).strip()

            last_sb = script_blocks[-1]
            last_sb.actions.append(ActionSpec(
                    type="remotion_picture",
                    config={
                        "template": "FilterTikTokSlide" if size=="tiktok" else "FilterDesktopSlide",
                        "image_filename": picture_filename,
                        "title": picture_title,
                        "target_name": last_sb.id,
                        "workdir": ".",
                    }
                ))
            continue

        # ------------------------------------------------
        # 2. Normal text line
        # ------------------------------------------------
        text = line
        character = default_character

        match_new = re.match(r'^"([^"]+)":\s*(.+)$', line)
        if match_new:
            character = match_new.group(1).strip()
            text = match_new.group(2).strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
        else:
            if ":" in line and not line.startswith("http"):
                prefix, rest = line.split(":", 1)
                if prefix.strip():
                    character = prefix.strip()
                    text = rest.strip()

        # Build ScriptBlock
        sb = ScriptBlock(
            id=f"L{line_index}",
            text=text,
            actions=[]
        )

        # ------------------------------------
        # Step 1: fish_audio
        # ------------------------------------
        sb.actions.append(ActionSpec(
            type="fish_audio",
            config={
                "text": text,
                "character": character,
                "target_name": sb.id,
                "workdir": ".",
            }
        ))

        # ------------------------------------
        # Step 2: text_video / extract_background_segment
        # ------------------------------------
        if background_video:
            sb.actions.append(ActionSpec(
                type="extract_background_segment",
                config={
                    "background_video": background_video,
                    "target_name": sb.id,
                    "workdir": ".",
                }
            ))
        else:
            sb.actions.append(ActionSpec(
                type="text_video",
                config={
                    "text": text,
                    "target_name": sb.id,
                    "workdir": ".",
                }
            ))

        # ------------------------------------
        # Step 3: remotion_picture
        # 加规则：如果上一句角色 != 当前角色 → appear: true
        # ------------------------------------
        slide_template = "OverlapCharacterTiktok" if size == "tiktok" else "OverlapCharacter"

        # 🔥 动态生成 config
        picture_config = {
            "template": slide_template,
            "character": character,
            "target_name": sb.id,
            "workdir": ".",
        }

        # 👇 角色变化 → 加 appear: true
        if prev_character is not None and prev_character != character:
            picture_config["appear"] = True

        sb.actions.append(ActionSpec(
            type="remotion_picture",
            config=picture_config
        ))

        # 收尾
        script_blocks.append(sb)
        prev_character = character  # 👈 更新上一行角色
        line_index += 1

    return script_blocks
