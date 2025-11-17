#!/usr/bin/env python3
"""
Script parsing logic for project generation.
Handles parsing of script text into blocks with support for:
- Character specification: "character_name": xxxx
- Picture blocks: [Lx.png:picture title...]
"""

from typing import Any, Dict, List
import re


def parse_script_lines(
    script_text: str,
    default_character: str,
    slide_template: str = "FilterTikTokSlide",
) -> List[Dict[str, Any]]:
    """
    Parse script text into blocks with support for character specification and picture blocks.
    
    Rules:
    1. If a line begins with "character_name": xxxx, use that character for the text
    2. If an entire line is [Lx.png:picture title...], treat it as a picture block
       attached to the previous line, adding info to extra_info field
    
    Args:
        script_text: The script text to parse
        default_character: Default character to use if not specified
    
    Returns:
        List of block dictionaries
    """
    blocks: List[Dict[str, Any]] = []
    if not script_text:
        return blocks

    line_index = 1
    lines = script_text.splitlines()
    
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        
        if not line:
            i += 1
            continue

        # Check if this is a picture block: [Lx.png:picture title...]
        picture_match = re.match(r'^\[([^:]+):(.+)\]$', line)
        if picture_match:
            picture_filename = picture_match.group(1).strip()
            picture_title = picture_match.group(2).strip()
            
            # Attach to the previous block if it exists
            if blocks:
                last_block = blocks[-1]
                if "extra_info" not in last_block:
                    last_block["extra_info"] = {}
                
                last_block["extra_info"]["single_picture"] = picture_filename
                last_block["extra_info"]["title"] = picture_title
                last_block["extra_info"]["template"] = slide_template
            # If no previous block, create a new block with picture info
            else:
                blocks.append({
                    "id": f"L{line_index}",
                    "text": picture_title,
                    "voice": picture_title,
                    "character": default_character or None,
                    "extra_info": {
                        "single_picture": picture_filename,
                        "title": picture_title,
                        "template": slide_template,
                    }
                })
                line_index += 1
        else:
            # Regular text line
            text = line
            character = default_character

            # Check if line begins with "character_name": xxxx
            # Pattern: "character_name": "text" or "character_name": text
            character_match = re.match(r'^"([^"]+)":\s*(.+)$', line)
            if character_match:
                character = character_match.group(1).strip()
                text = character_match.group(2).strip()
                # Remove surrounding quotes if present
                if text.startswith('"') and text.endswith('"'):
                    text = text[1:-1]
            # Fallback to old format: character: text
            elif ":" in line and not line.startswith("http"):
                prefix, rest = line.split(":", 1)
                if prefix.strip():
                    character = prefix.strip()
                    text = rest.strip()

            blocks.append({
                "id": f"L{line_index}",
                "text": text,
                "voice": text,
                "character": character or None,
            })
            line_index += 1
        
        i += 1

    return blocks

