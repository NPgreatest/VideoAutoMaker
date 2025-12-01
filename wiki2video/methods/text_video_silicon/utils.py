#!/usr/bin/env python3
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Union

def _run_ffmpeg(cmd: list[str]) -> bool:
    """Execute FFmpeg command and print diagnostic output on failure."""
    print(f"[ffmpeg] {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("[ffmpeg] ❌ FFmpeg failed:")
        print(proc.stderr)
        return False
    return True


def _get_video_duration_sec(video_path: Path) -> float:
    """Return duration (seconds) using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def resize_video_duration(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    target_duration_sec: float
) -> float:
    input_path = Path(input_path)
    output_path = Path(output_path)

    base_dur = _get_video_duration_sec(input_path)
    if base_dur <= 0:
        print("[resize] ⚠️ Cannot read duration.")
        return 0.0

    playback_scale = base_dur / target_duration_sec
    print(f"[resize] Base={base_dur:.2f}s → Target={target_duration_sec:.2f}s  scale={playback_scale:.3f}")

    has_audio = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(input_path)],
        capture_output=True, text=True
    ).stdout.strip() != ""

    # 视频: setpts = 1/scale
    video_filter = f"[0:v]setpts={1/playback_scale:.6f}*PTS[v]"

    if has_audio:
        # 音频：atempo = scale (同速)
        atempo_filters = []
        r = playback_scale
        while r < 0.5 or r > 2.0:
            if r < 0.5:
                atempo_filters.append("atempo=0.5")
                r /= 0.5
            else:
                atempo_filters.append("atempo=2.0")
                r /= 2.0
        atempo_filters.append(f"atempo={r:.3f}")
        atempo = ",".join(atempo_filters)
        audio_filter = f"[0:a]{atempo}[a]"
        filter_complex = f"{video_filter};{audio_filter}"
        map_args = ["-map", "[v]", "-map", "[a]"]
    else:
        print("[resize] ℹ️ No audio stream detected — resizing video only.")
        filter_complex = video_filter
        map_args = ["-map", "[v]"]

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-filter_complex", filter_complex,
        *map_args,
        "-c:v", "libx264", "-c:a", "aac",
        str(output_path)
    ]

    if _run_ffmpeg(cmd):
        new_dur = _get_video_duration_sec(output_path)
        print(f"[resize] ✅ Output: {output_path} ({new_dur:.2f}s)")
        return new_dur
    else:
        print("[resize] ❌ Failed to resize (see FFmpeg output).")
        return 0.0
