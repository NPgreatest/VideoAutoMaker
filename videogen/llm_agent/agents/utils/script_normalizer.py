

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path


IMAGE_MARKER_PATTERN = re.compile(r"^\[.*\]$")

# 允许的字符：字母、数字、空格、逗号、句号、单引号
ALLOWED_PATTERN = re.compile(r"[^A-Za-z0-9\s\',\.]")

def normalize_line(line: str) -> str:
    """
    Normalize a single line of script:
    - Preserve image markers exactly
    - Remove disallowed punctuation
    - Strip excessive spaces
    """
    stripped = line.strip()

    # --- CASE 1: image marker like [abc.png: ] → keep unchanged ---
    if IMAGE_MARKER_PATTERN.match(stripped):
        return stripped

    # --- CASE 2: normal narration text ---
    cleaned = ALLOWED_PATTERN.sub("", stripped)  # remove unwanted chars
    cleaned = re.sub(r"\s+", " ", cleaned).strip()  # collapse multiple spaces
    return cleaned


def normalize_script(text: str) -> str:
    """
    Normalize full script:
    - Ensure only one newline between lines
    - Normalize content line by line
    """
    lines = text.split("\n")
    out_lines = []

    for raw in lines:
        line = normalize_line(raw)
        if line == "":
            continue
        out_lines.append(line)

    # ensure exactly one newline between lines
    return "\n".join(out_lines).strip()


