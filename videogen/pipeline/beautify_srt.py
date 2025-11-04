#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


# Chinese and common punctuation marks. We keep them as individual tokens and break lines after them
PUNCTUATION_PATTERN = r"[，。！？；：、,.!?;:（）()《》“”\"'——…]"


def tokenize_with_punct(text: str) -> List[Tuple[str, bool]]:
    """Split text into a list of (token, is_punct). Keeps punctuation as separate tokens.
    Collapses whitespace; Chinese text typically has none, but we normalize just in case.
    """
    text = re.sub(r"\s+", "", text)
    parts = re.split(f"({PUNCTUATION_PATTERN})", text)
    tokens: List[Tuple[str, bool]] = []
    for p in parts:
        if not p:
            continue
        if re.fullmatch(PUNCTUATION_PATTERN, p):
            tokens.append((p, True))
        else:
            tokens.append((p, False))
    return tokens


def wrap_into_lines(tokens: List[Tuple[str, bool]], max_len: int = 8) -> List[str]:
    """Greedy wrap tokens into lines not exceeding max_len, preferring breaks after punctuation.
    After any punctuation token, force a line break.
    """
    lines: List[str] = []
    current: str = ""

    def flush() -> None:
        nonlocal current
        if current:
            lines.append(current)
            current = ""

    for tok, is_punct in tokens:
        if not tok:
            continue
        if not is_punct:
            # If token is longer than max_len, chunk it
            i = 0
            n = len(tok)
            while i < n:
                chunk = tok[i : i + max_len]
                if not current:
                    current = chunk
                elif len(current) + len(chunk) <= max_len:
                    current += chunk
                else:
                    flush()
                    current = chunk
                i += len(chunk)
        else:
            # punctuation as single token
            if not current:
                # put punctuation alone if needed
                current = tok
            elif len(current) + len(tok) <= max_len:
                current += tok
            else:
                flush()
                current = tok
            # always break after punctuation
            flush()

    if current:
        flush()
    return lines


def merge_short_lines(lines: List[str], min_len: int = 4, max_len: int = 8) -> List[str]:
    """Merge lines shorter than min_len with the following content, then re-wrap to <= max_len.
    This is a second pass to avoid dangling very short lines.
    """
    if not lines:
        return []
    i = 0
    merged: List[str] = []
    buffer = ""

    def flush_buffer():
        nonlocal buffer
        if buffer:
            # naive rewrap buffer into <= max_len chunks
            start = 0
            while start < len(buffer):
                merged.append(buffer[start : start + max_len])
                start += max_len
            buffer = ""

    while i < len(lines):
        line = lines[i]
        if len(line) < min_len and i + 1 < len(lines):
            # merge with next and continue; don't flush yet
            buffer += line
            i += 1
            continue
        if buffer:
            buffer += line
            flush_buffer()
        else:
            merged.append(line)
        i += 1

    if buffer:
        flush_buffer()

    # Ensure final safety: no line exceeds max_len
    final: List[str] = []
    for ln in merged:
        if len(ln) <= max_len:
            final.append(ln)
        else:
            start = 0
            while start < len(ln):
                final.append(ln[start : start + max_len])
                start += max_len
    return final


def beautify_text_block(text_block: str) -> str:
    """Beautify a single SRT text block according to rules.
    - Prefer splitting by punctuation and wrap to <=8 chars
    - Ensure punctuation ends a line
    - Merge lines with <4 chars with subsequent content, then rewrap to <=8
    """
    # Combine all original lines and remove spaces
    flat = re.sub(r"\s+", "", text_block.strip())
    tokens = tokenize_with_punct(flat)
    lines = wrap_into_lines(tokens, max_len=8)
    lines = merge_short_lines(lines, min_len=4, max_len=8)

    # Remove all punctuation and non Chinese/English letters in the final output
    def keep_cjk_english(s: str) -> str:
        # keep only A-Za-z and \u4e00-\u9fff
        return re.sub(r"[^A-Za-z\u4e00-\u9fff]", "", s)

    cleaned = [keep_cjk_english(l) for l in lines]
    cleaned = [l for l in cleaned if l]

    # Re-merge and ensure <=8 after stripping symbols
    cleaned = merge_short_lines(cleaned, min_len=4, max_len=8)

    # Final safety wrap
    final: List[str] = []
    for l in cleaned:
        if len(l) <= 8:
            final.append(l)
        else:
            start = 0
            while start < len(l):
                final.append(l[start : start + 8])
                start += 8
    return "\n".join(final)


def parse_srt_blocks(content: str) -> List[Tuple[str, str, str]]:
    """Parse SRT content into list of (index, timing, text) blocks."""
    blocks: List[Tuple[str, str, str]] = []
    parts = re.split(r"\n\s*\n", content.strip(), flags=re.M)
    for part in parts:
        lines = part.splitlines()
        if len(lines) < 2:
            continue
        idx = lines[0].strip()
        timing = lines[1].strip()
        text = "\n".join(lines[2:]).strip()
        blocks.append((idx, timing, text))
    return blocks


def render_srt_blocks(blocks: List[Tuple[str, str, str]]) -> str:
    out_lines: List[str] = []
    for idx, timing, text in blocks:
        out_lines.append(str(idx))
        out_lines.append(timing)
        out_lines.extend(text.splitlines())
        out_lines.append("")  # blank line between blocks
    return "\n".join(out_lines).rstrip() + "\n"


def beautify_srt_at_path(srt_path: Path, dest_path: Path | None = None) -> Path:
    raw = srt_path.read_text(encoding="utf-8")
    blocks = parse_srt_blocks(raw)
    new_blocks: List[Tuple[str, str, str]] = []
    for idx, timing, text in blocks:
        pretty = beautify_text_block(text)
        new_blocks.append((idx, timing, pretty))
    out_path = dest_path if dest_path is not None else srt_path
    out_path.write_text(render_srt_blocks(new_blocks), encoding="utf-8")
    return out_path


def main():
    load_dotenv()
    project_name = os.getenv("PROJECT_NAME")
    if not project_name:
        raise SystemExit("Please set PROJECT_NAME in .env")
    project_dir = Path(f"project/{project_name}")
    srt_path = project_dir / "_work" / "full.srt"
    if not srt_path.exists():
        raise SystemExit(f"Subtitle not found: {srt_path}")
    dest = project_dir / "_work" / f"{project_name}.srt"
    out = beautify_srt_at_path(srt_path, dest)
    print(f"[srt] ✅ beautified -> {out}")


if __name__ == "__main__":
    main()


