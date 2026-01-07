

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path


IMAGE_MARKER_PATTERN = re.compile(r"^\[.*\]$")

# 允许的字符：字母（包括中文）、数字、空格、常见标点符号
# \u4e00-\u9fff 是中文字符（CJK统一汉字）
# \u3400-\u4dbf 是扩展A区中文字符
# \u3000-\u303f 是中文标点和符号
# \uff00-\uffef 是全角字符范围（包括全角字母、数字、标点）
# A-Za-z0-9 是英文字母和数字
# \s 是空白字符
# 加上常见的中英文标点符号
ALLOWED_PATTERN = re.compile(
    r"[^\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffefA-Za-z0-9\s\',\.。！？，、；：""''（）【】《》…—\-]",
    re.UNICODE
)

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


