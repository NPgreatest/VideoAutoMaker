#!/usr/bin/env python3
"""
Script parsing with:
- Normal dialogue
- Picture lines [img.png:title]
- Slide-only title clip [: title]
- Flags:
    -blank
    -imageMode='center'
"""

from typing import Any, Dict, List
import re
from videogen.schema.action_spec import ActionSpec
from videogen.schema.project_schema import ScriptBlock


def _extract_character_key(raw: str) -> str:
    if not raw:
        return raw
    match = re.search(r"\(([^)]+)\)", raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def parse_script_lines(
    script_text: str,
    default_character: str,
    size: str = "tiktok",
    background_video: str = None,
    show_character_overlay: bool = True,
) -> List[ScriptBlock]:

    script_blocks: List[ScriptBlock] = []
    if not script_text:
        return script_blocks

    line_index = 1
    lines = script_text.splitlines()

    prev_character = None
    character_sides: Dict[str, str] = {}
    default_character_key = _extract_character_key(default_character)

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # ============================================
        # 🔥 global flag extraction
        # ============================================
        blank_flag = bool(re.search(r"-blank\b", line))
        image_mode_match = re.search(r"-imageMode='([^']+)'", line)
        custom_image_mode = image_mode_match.group(1) if image_mode_match else None
        appear_flag = bool(re.search(r"--appear", line))

        # remove flags for main parsing
        line_clean = re.sub(r"-blank", "", line)
        line_clean = re.sub(r"-imageMode='([^']+)'", "", line_clean).strip()
        line_clean = re.sub(r"--appear", "", line_clean).strip()
        print(line_clean, end="\n\n")
        # ============================================
        # 0️⃣ Title-only slide: [: title text]
        # ============================================
        title_slide_match = re.match(r"^\[:\s*(.+)\]$", line_clean)
        if title_slide_match:
            title = title_slide_match.group(1).strip()

            last_sb = script_blocks[-1]

            template_name = "Slide-Portrait" if size == "tiktok" else "Slide-Landscape"

            cfg = {
                "template": template_name,
                "title": title,
                "image_filename": "",
                "target_name": last_sb.id,
                "workdir": ".",
            }

            if custom_image_mode:
                cfg["imageMode"] = custom_image_mode
            if appear_flag:
                cfg["appear"] = True

            last_sb.actions.append(ActionSpec(type="remotion_picture", config=cfg))
            continue

        # ====================================================
        # 1️⃣ Picture-only: [img.png:title]
        # ====================================================
        picture_match = re.match(r'^\[([^:]+):(.*)\]$', line_clean)
        if picture_match:
            picture_filename = picture_match.group(1).strip()
            picture_title = picture_match.group(2).strip()

            last_sb = script_blocks[-1]

            template_name = "Slide-Portrait" if size == "tiktok" else "Slide-Landscape"

            cfg = {
                "template": template_name,
                "image_filename": picture_filename,
                "title": picture_title,
                "target_name": last_sb.id,
                "workdir": ".",
            }

            if custom_image_mode:
                cfg["imageMode"] = custom_image_mode
            if appear_flag:
                cfg["appear"] = True

            last_sb.actions.append(ActionSpec(
                type="remotion_picture",
                config=cfg,
            ))
            continue

        # ====================================================
        # 2️⃣ Normal text (dialogue)
        # ====================================================
        text = line_clean
        character = default_character_key

        match_new = re.match(r'^"([^"]+)":\s*(.+)$', line_clean)
        if match_new:
            character = _extract_character_key(match_new.group(1).strip())
            text = match_new.group(2).strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
        else:
            if ":" in line_clean and not line_clean.startswith("http"):
                prefix, rest = line_clean.split(":", 1)
                if prefix.strip():
                    character = _extract_character_key(prefix.strip())
                    text = rest.strip()

        # ============================================
        # Create ScriptBlock
        # ============================================
        sb = ScriptBlock(
            id=f"L{line_index}",
            text=text,
            actions=[],
        )

        # --- Step1: audio ---
        sb.actions.append(ActionSpec(
            type="fish_audio",
            config={
                "text": text,
                "character": character,
                "target_name": sb.id,
                "workdir": ".",
            }
        ))

        # --- Step2: background video OR text_video ---
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
            if not blank_flag:   # 👈 NEW
                sb.actions.append(ActionSpec(
                    type="text_video",
                    config={
                        "text": text,
                        "target_name": sb.id,
                        "workdir": ".",
                    }
                ))
                sb.actions.append(ActionSpec(
                    type="remotion_picture",
                    config={
                    "template": "ElasticClip",
                    "workdir": ".",
                    "target_name": sb.id,
                    }
                ))

        # ============================================
        # Step 3: Character overlay (remotion_picture)
        # ============================================
        if show_character_overlay:
            slide_template = (
                "CharacterOverlay-Portrait" if size == "tiktok"
                else "CharacterOverlay-Landscape"
            )

            picture_config = {
                "template": slide_template,
                "character": character,
                "target_name": sb.id,
                "workdir": ".",
            }

            if character not in character_sides:
                if len(character_sides) == 0:
                    character_sides[character] = "left"
                elif len(character_sides) == 1:
                    character_sides[character] = "right"
                else:
                    character_sides[character] = "left"

            picture_config["appear_from"] = character_sides[character]

            if prev_character == character:
                picture_config["appear"] = True

            if custom_image_mode:
                picture_config["imageMode"] = custom_image_mode

            sb.actions.append(ActionSpec(
                type="remotion_picture",
                config=picture_config
            ))

        script_blocks.append(sb)
        prev_character = character
        line_index += 1

    return script_blocks
