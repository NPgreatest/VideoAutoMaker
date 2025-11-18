#!/usr/bin/env python3
"""
Script parsing logic for project generation.
Generates ScriptBlock + ActionSpec[] suitable for the new pipeline architecture.
"""

from typing import Any, Dict, List
import re
import uuid

from videogen.schema.action_spec import ActionSpec
from videogen.schema.project_schema import ScriptBlock


def new_action_id() -> str:
    return uuid.uuid4().hex[:8]

def parse_script_lines(
    script_text: str,
    default_character: str,
    size: str = "tiktok",
    background_video: str = None,   # ← 新增参数
) -> List[ScriptBlock]:
    """
    Parse script text and produce ScriptBlock[] with ActionSpec[],
    matching the new static DSL → runtime job pipeline architecture.

    If background_video is provided → use extract_background_segment
    Else → use text_video
    """

    script_blocks: List[ScriptBlock] = []
    if not script_text:
        return script_blocks

    line_index = 1
    lines = script_text.splitlines()
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        i += 1

        if not line:
            continue

        # ------------------------------------
        # 1. picture block: [L1.png:title]
        # ------------------------------------
        picture_match = re.match(r'^\[([^:]+):(.+)\]$', line)
        if picture_match:
            picture_filename = picture_match.group(1).strip()
            picture_title = picture_match.group(2).strip()
            slide_template = "FilterTikTokSlide" if size=="tiktok" else "FilterDesktopSlide"
            if script_blocks:
                last_block = script_blocks[-1]

                # ⭐ 链式依赖：依赖当前 block 的最后一个 action
                prev_action_id = last_block.actions[-1].id

                remotion_action = ActionSpec(
                    id=new_action_id(),
                    type="remotion_picture",
                    prev_ids=[prev_action_id],  # ← 关键！链式依赖
                    config={
                        "target_name": last_block.id,
                        "template": slide_template,
                        "image_filename": picture_filename,
                        "title": picture_title,
                        "description": "",
                        "workdir": ".",
                    }
                )
                last_block.actions.append(remotion_action)
            else:
                sb = ScriptBlock(id=f"L{line_index}", text=picture_title)
                sb.actions.append(ActionSpec(
                    id=new_action_id(),
                    type="remotion_picture",
                    prev_ids=[],
                    config={
                        "target_name": sb.id,
                        "template": slide_template,
                        "image_filename": picture_filename,
                        "title": picture_title,
                        "description": "",
                        "workdir": ".",
                    }
                ))
                script_blocks.append(sb)
                line_index += 1

            continue

        # ------------------------------------
        # 2. text line with character support
        # ------------------------------------
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

        # ------------------------------------
        # Construct ScriptBlock
        # ------------------------------------
        sb = ScriptBlock(
            id=f"L{line_index}",
            text=text,
            actions=[]
        )

        # ------------------------------------
        # Step 1: fish_audio
        # ------------------------------------
        audio_action_id = new_action_id()

        # fish_audio.prev_ids = 上一个 block 的 fish_audio
        prev_fish_audio_id = None
        if script_blocks:
            last_block = script_blocks[-1]
            for act in last_block.actions:
                if act.type == "fish_audio":
                    prev_fish_audio_id = act.id
                    break

        sb.actions.append(ActionSpec(
            id=audio_action_id,
            type="fish_audio",
            prev_ids=[prev_fish_audio_id] if prev_fish_audio_id else [],
            config={
                "text": text,
                "target_name": sb.id,
                "character": character,
                "workdir": ".",
            }
        ))

        # ------------------------------------
        # Step 2: SELECT VIDEO METHOD
        # ------------------------------------
        video_action_id = new_action_id()

        if background_video:
            video_type = "extract_background_segment"
            video_config = {
                "background_video": background_video,
                "text": text,
                "target_name": sb.id,
                "workdir": ".",
            }
        else:
            video_type = "text_video"
            video_config = {
                "text": text,
                "target_name": sb.id,
                "workdir": ".",
            }

        sb.actions.append(ActionSpec(
            id=video_action_id,
            type=video_type,
            prev_ids=[audio_action_id],  # ← 只依赖当前 fish_audio
            config=video_config,
        ))

        # ------------------------------------
        # Step 3: remotion_picture chain
        # ------------------------------------
        def add_remotion(template_name, extra_config=None):
            """
            Add a remotion_picture node that ALWAYS depends on
            the previous action inside this block.
            """
            prev_action_id = sb.actions[-1].id  # ← 链式依赖的关键点
            remotion_id = new_action_id()

            conf = {
                "template": template_name,
                "workdir": ".",
                "target_name": sb.id,
            }
            if extra_config:
                conf.update(extra_config)

            sb.actions.append(ActionSpec(
                id=remotion_id,
                type="remotion_picture",
                prev_ids=[prev_action_id],  # ← 链式依赖
                config=conf
            ))

        slide_template = "OverlapCharacterTiktok" if size == "tiktok" else "OverlapCharacter"

        add_remotion(slide_template ,extra_config={
            "text": text,
            "character": character,
            "workdir": ".",
        })

        script_blocks.append(sb)
        line_index += 1

    return script_blocks
