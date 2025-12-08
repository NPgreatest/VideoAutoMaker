#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple


# Chinese and common punctuation marks. We keep them as individual tokens and break lines after them
PUNCTUATION_PATTERN = r"[，。！？；：、,.!?;:（）()《》“”\"'——…]"


def tokenize_with_punct(text: str) -> List[Tuple[str, bool]]:
    """Split text into a list of (token, is_punct). Keeps punctuation as separate tokens.
    Separates English words from Chinese characters to avoid splitting English words.
    Preserves spaces between English words, but collapses multiple spaces to single space.
    """
    # 压缩多个空格为单个空格，保留英文单词之间的分隔
    text = re.sub(r"\s+", " ", text).strip()
    # First split by punctuation
    parts = re.split(f"({PUNCTUATION_PATTERN})", text)
    tokens: List[Tuple[str, bool]] = []

    for p in parts:
        if not p:
            continue
        if re.fullmatch(PUNCTUATION_PATTERN, p):
            tokens.append((p, True))
        else:
            # Split mixed text into English words, spaces, and Chinese characters
            # Use a pattern that captures English words, spaces, and everything else
            mixed_parts = re.split(r'([A-Za-z0-9]+|\s+)', p)
            for mp in mixed_parts:
                if not mp:
                    continue
                if re.fullmatch(r'[A-Za-z0-9]+', mp):
                    # English word - keep as one token
                    tokens.append((mp, False))
                elif re.fullmatch(r'\s+', mp):
                    # Space - keep as a special token (not punctuation, but needs special handling)
                    tokens.append((" ", False))  # Single space token
                else:
                    # Chinese or other characters - keep as one token block
                    tokens.append((mp, False))
    return tokens


def split_preserving_english(s: str, max_len: int) -> List[str]:
    """Split string into lines <= max_len without breaking English [A-Za-z0-9]+ sequences."""
    if not s:
        return []
    parts: List[str] = []
    current = ""
    i = 0
    n = len(s)

    def is_eng(ch: str) -> bool:
        return bool(re.match(r'[A-Za-z0-9]', ch))

    while i < n:
        ch = s[i]
        if is_eng(ch):
            # collect full English "word"
            j = i
            while j < n and is_eng(s[j]):
                j += 1
            word = s[i:j]
            # 如果单词本身超过 max_len，就允许整块溢出一行（不拆）
            if not current:
                current = word
            elif len(current) + len(word) <= max_len:
                current += word
            else:
                parts.append(current)
                current = word
            i = j
        else:
            # 非英文字符按单字计
            if not current:
                current = ch
            elif len(current) + 1 <= max_len:
                current += ch
            else:
                parts.append(current)
                current = ch
            i += 1

    if current:
        parts.append(current)
    return parts


def wrap_into_lines(tokens: List[Tuple[str, bool]], max_len: int = 8) -> List[str]:
    """Greedy wrap tokens into lines not exceeding max_len, preferring breaks after punctuation.
    After any punctuation token, force a line break.
    English tokens ([A-Za-z0-9]+) are never split.
    Preserves spaces between English words.
    """
    lines: List[str] = []
    current: str = ""
    pending_space = False  # Track if we need to add a space before next word

    def flush() -> None:
        nonlocal current, pending_space
        if current:
            lines.append(current)
            current = ""
        pending_space = False  # Reset space flag on flush

    def is_english_word(text: str) -> bool:
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    for tok, is_punct in tokens:
        if not tok:
            continue

        if not is_punct:
            if tok == " ":
                # Space token - mark that next English word needs a space before it
                # Only set flag if current line ends with an English character
                if current and current[-1].isalnum():
                    pending_space = True
                # If current is empty or ends with non-English, ignore the space
            elif is_english_word(tok):
                # 英文整词，不拆，并在前面添加空格（如果需要）
                space_len = 1 if pending_space else 0
                pending_space = False  # Reset after using
                
                if not current:
                    current = tok
                    if len(current) > max_len:
                        flush()
                elif len(current) + space_len + len(tok) <= max_len:
                    if space_len > 0:
                        current += " " + tok
                    else:
                        current += tok
                else:
                    flush()
                    current = tok
                    if len(current) > max_len:
                        flush()
            else:
                # 非英文（中文等），按字符切，优先填满当前行
                # Reset pending_space since we're not dealing with English
                pending_space = False
                i = 0
                n = len(tok)
                while i < n:
                    ch = tok[i]
                    if not current:
                        current = ch
                    elif len(current) + 1 <= max_len:
                        current += ch
                    else:
                        flush()
                        current = ch
                    i += 1
        else:
            # punctuation as single token, keep then换行
            pending_space = False  # Reset space flag before punctuation
            if not current:
                current = tok
            elif len(current) + len(tok) <= max_len:
                current += tok
            else:
                flush()
                current = tok
            flush()  # always break after punctuation

    if current:
        flush()
    return lines


def merge_short_lines(lines: List[str], min_len: int = 4, max_len: int = 8) -> List[str]:
    """Merge lines shorter than min_len with the following content.
    Re-wrap using split_preserving_english to avoid breaking English words.
    Preserves spaces between English words when merging.
    """
    if not lines:
        return []

    merged: List[str] = []
    buffer = ""

    def flush_buffer():
        nonlocal buffer
        if buffer:
            merged.extend(split_preserving_english(buffer, max_len))
            buffer = ""

    def needs_space_between(s1: str, s2: str) -> bool:
        """Check if we need a space between two strings (for English words)."""
        if not s1 or not s2:
            return False
        # Need space if both end and start with alphanumeric characters
        return s1[-1].isalnum() and s2[0].isalnum()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if len(line) < min_len and i + 1 < n:
            # 累积到 buffer，等下和后面的合并
            # Add space if needed when appending to buffer
            if buffer and needs_space_between(buffer, line):
                buffer += " " + line
            else:
                buffer += line
        else:
            if buffer:
                # Add space if needed when merging buffer with line
                if needs_space_between(buffer, line):
                    buffer += " " + line
                else:
                    buffer += line
                flush_buffer()
            else:
                merged.append(line)
        i += 1

    if buffer:
        flush_buffer()

    # 最终保证每行 <= max_len，同时不拆英文
    final: List[str] = []
    for ln in merged:
        if len(ln) <= max_len:
            final.append(ln)
        else:
            # For lines with spaces, use word-aware splitting
            if " " in ln:
                words = ln.split()
                current_line = ""
                for word in words:
                    if not current_line:
                        current_line = word
                    elif len(current_line) + 1 + len(word) <= max_len:
                        current_line += " " + word
                    else:
                        if current_line:
                            final.append(current_line)
                        current_line = word
                if current_line:
                    final.append(current_line)
            else:
                final.extend(split_preserving_english(ln, max_len))
    return final


def beautify_text_block(text_block: str) -> str:
    """Beautify a single SRT text block according to rules.
    - Prefer splitting by punctuation and wrap to <=8 chars
    - Ensure punctuation ends a line
    - Merge lines with <4 chars with subsequent content, then rewrap to <=8
    - Never split English words (A-Za-z0-9 sequences)
    - Preserve spaces between English words
    """
    # Preserve spaces but normalize multiple spaces to single space
    flat = re.sub(r"\s+", " ", text_block.strip())
    tokens = tokenize_with_punct(flat)
    lines = wrap_into_lines(tokens, max_len=8)
    lines = merge_short_lines(lines, min_len=4, max_len=8)

    # Remove punctuation but keep spaces and English/Chinese characters
    def keep_cjk_english_spaces(s: str) -> str:
        # keep A-Za-z0-9, \u4e00-\u9fff, %, +, and spaces
        # Remove punctuation but preserve word separators
        return re.sub(r"[^A-Za-z0-9\u4e00-\u9fff%\s+]", "", s)

    cleaned = [keep_cjk_english_spaces(l) for l in lines]
    # Normalize spaces: compress multiple spaces to single, but keep single spaces
    cleaned = [re.sub(r"\s+", " ", l).strip() for l in cleaned if l.strip()]

    # 再跑一次合并，仍然使用不拆英文的逻辑
    cleaned = merge_short_lines(cleaned, min_len=4, max_len=8)

    # Final safety: 用 split_preserving_english，彻底杜绝英文被切断
    # But we need to preserve spaces, so we'll handle it differently
    final: List[str] = []
    for l in cleaned:
        # For lines with spaces (English text), split preserving words and spaces
        if " " in l:
            # Split by spaces first, then wrap each word group
            words = l.split()
            current_line = ""
            for word in words:
                if not current_line:
                    current_line = word
                elif len(current_line) + 1 + len(word) <= 8:  # +1 for space
                    current_line += " " + word
                else:
                    if current_line:
                        final.append(current_line)
                    current_line = word
            if current_line:
                final.append(current_line)
        else:
            # No spaces, use original split logic
            final.extend(split_preserving_english(l, 8))

    return "\n".join([l for l in final if l])


def parse_timing(timing_str: str) -> Tuple[float, float]:
    """Parse SRT timing string (HH:MM:SS,mmm --> HH:MM:SS,mmm) into (start, end) seconds."""
    try:
        parts = timing_str.split(" --> ")
        if len(parts) != 2:
            return 0.0, 0.0
        
        def parse_time(time_str: str) -> float:
            # Format: HH:MM:SS,mmm or HH:MM:SS.mmm
            time_str = time_str.strip().replace(",", ".")
            hms, ms = time_str.rsplit(".", 1) if "." in time_str else (time_str, "0")
            h, m, s = map(int, hms.split(":"))
            return h * 3600 + m * 60 + s + float("0." + ms)
        
        start = parse_time(parts[0])
        end = parse_time(parts[1])
        return start, end
    except Exception:
        return 0.0, 0.0


def format_timing(start: float, end: float) -> str:
    """Format (start, end) seconds into SRT timing string."""
    def fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    
    return f"{fmt_time(start)} --> {fmt_time(end)}"


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences based on sentence-ending punctuation.
    Sentence endings: 。！？.?! and their combinations.
    """
    # Normalize text first
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    
    # Pattern for sentence endings: 。！？.?! (Chinese and English sentence endings)
    # Split by sentence-ending punctuation, keeping the punctuation with the sentence
    # Use positive lookahead to split but keep the delimiter
    sentence_end_pattern = r"[。！？.?!]+"
    
    # Split the text by sentence endings, but keep the endings
    parts = re.split(f"({sentence_end_pattern})", text)
    
    sentences = []
    current = ""
    
    for part in parts:
        if not part:
            continue
        current += part
        # Check if current part ends with sentence-ending punctuation
        if re.search(sentence_end_pattern, part):
            # Found a complete sentence
            sentence = current.strip()
            if sentence:
                sentences.append(sentence)
            current = ""
    
    # Add remaining text as last sentence if any
    if current.strip():
        sentences.append(current.strip())
    
    # Filter out empty sentences
    return [s for s in sentences if s]


def split_block_into_sentences(idx: str, timing: str, text: str):
    # 如果是 segment → 一律不处理
    if text.startswith("__SEG__:"):
        pure = text.replace("__SEG__:", "", 1).strip()
        return [(idx, timing, pure)]
    """Split a single SRT block into multiple blocks, one per sentence.
    Time is distributed proportionally based on text length.
    
    Note: If the text is from a segment (already split), we should not split it again.
    We detect this by checking if the text is relatively short (likely a single phrase).
    """
    # 检测是否是来自 segment 的短语
    # segment 文本通常较短，且可能以标点结尾（但不会包含多个句子）
    # 如果文本较短（<= 30 字符）且只包含一个句末标点（在末尾），可能是 segment，不分割
    text_stripped = text.strip()
    text_len = len(text_stripped)
    
    # 检查是否只有一个句末标点，且在末尾
    sentence_ends = re.findall(r"[。！？.?!]+", text_stripped)
    has_single_end_at_tail = (
        len(sentence_ends) == 1 and 
        text_stripped.rstrip().endswith(tuple("。！？.?!"))
    )
    
    # 如果文本较短且只有一个句末标点在末尾，可能是 segment 短语，不分割
    # 这样可以保留 segment 的原始时间戳
    if text_len <= 30 and (has_single_end_at_tail or not sentence_ends):
        # 只美化，不分割，保留原始时间戳
        pretty = beautify_text_block(text)
        return [(idx, timing, pretty)]
    
    sentences = split_into_sentences(text)
    
    if len(sentences) <= 1:
        # No splitting needed, just beautify and return
        pretty = beautify_text_block(text)
        return [(idx, timing, pretty)]
    
    # Parse timing
    start_sec, end_sec = parse_timing(timing)
    duration = end_sec - start_sec
    
    # Calculate total text length (for proportional distribution)
    total_length = sum(len(s) for s in sentences)
    if total_length == 0:
        # Fallback: equal distribution
        time_per_sentence = duration / len(sentences)
    else:
        # Proportional distribution
        time_per_sentence = None
    
    # Create blocks for each sentence
    result = []
    current_start = start_sec
    current_idx = int(idx)
    
    for i, sentence in enumerate(sentences):
        if i == len(sentences) - 1:
            # Last sentence gets remaining time
            current_end = end_sec
        else:
            if time_per_sentence is None:
                # Proportional distribution
                sentence_ratio = len(sentence) / total_length
                current_end = current_start + duration * sentence_ratio
            else:
                # Equal distribution
                current_end = current_start + time_per_sentence
        
        # Beautify the sentence
        pretty = beautify_text_block(sentence)
        
        # Create new block
        new_timing = format_timing(current_start, current_end)
        result.append((str(current_idx), new_timing, pretty))
        
        current_start = current_end
        current_idx += 1
    
    return result


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
        out_lines.append("")
    return "\n".join(out_lines).rstrip() + "\n"


def beautify_srt_at_path(srt_path: Path, dest_path: Path | None = None) -> Path:
    raw = srt_path.read_text(encoding="utf-8")
    blocks = parse_srt_blocks(raw)
    new_blocks: List[Tuple[str, str, str]] = []
    
    # Track index for renumbering after splitting
    next_idx = 1
    
    for idx, timing, text in blocks:
        # Split block into sentences if it contains multiple sentences
        # Pass the starting index, and the function will handle incrementing
        split_blocks = split_block_into_sentences(str(next_idx), timing, text)
        
        # Add all split blocks (they already have correct indices)
        new_blocks.extend(split_blocks)
        
        # Update next index for next block
        next_idx += len(split_blocks)
    
    out_path = dest_path if dest_path is not None else srt_path
    out_path.write_text(render_srt_blocks(new_blocks), encoding="utf-8")
    return out_path

