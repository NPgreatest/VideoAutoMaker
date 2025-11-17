#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.pipeline.schema import ScriptBlock


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


def _get_video_resolution(video_path: Path) -> tuple[int, int]:
    """Return video resolution (width, height) using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        lines = result.stdout.strip().split('\n')
        width = int(lines[0]) if len(lines) > 0 else 1920
        height = int(lines[1]) if len(lines) > 1 else 1080
        return width, height
    except Exception:
        # Default to 1920x1080 if cannot read
        return 1920, 1080


@register_method
class ExtractBackgroundSegmentMethod(BaseMethod):
    NAME = "extract_background_segment"
    OUTPUT_KIND = "video"

    def __init__(self) -> None:
        super().__init__()

    def generate_prompt(self, text: str, context: str = None) -> str:
        """Not used for background video extraction."""
        return ""

    def run(
        self,
        *,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: Optional[int] = None,
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        """
        Extract a segment from the background video.
        
        The segment start time is calculated based on cumulative previous clip durations.
        The segment duration matches the audio duration for this block.
        """
        try:
            # Get background video path from project JSON
            project_dir = workdir / "project" / project
            project_json_path = project_dir / f"{project}.json"
            
            if not project_json_path.exists():
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": f"Project JSON not found: {project_json_path}",
                }

            # Read project JSON to get background_video path
            from videogen.pipeline.utils import read_json
            project_data = read_json(project_json_path)
            background_video_path = project_data.get("background_video")
            
            if not background_video_path:
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": "No background_video specified in project",
                }

            # Resolve background video path (can be relative or absolute)
            bg_video = Path(background_video_path)
            if not bg_video.is_absolute():
                # Resolve relative path from project root
                project_root = Path.cwd()
                bg_video = (project_root / bg_video).resolve()
            
            if not bg_video.exists():
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": f"Background video not found: {bg_video}",
                }

            # Get audio duration in seconds
            if not duration_ms:
                # Try to get from block's audio_generation
                if block and block.audio_generation and block.audio_generation.ok:
                    duration_ms = block.audio_generation.meta.get('total_duration', None)
                
                if not duration_ms:
                    return {
                        "ok": False,
                        "artifacts": [],
                        "meta": {},
                        "error": "No duration_ms provided and cannot get from audio_generation",
                    }

            duration_sec = duration_ms / 1000.0

            # Calculate start time based on cumulative previous clip durations
            # Get all blocks before current one
            script_blocks = project_data.get("script", [])
            current_block_idx = None
            for idx, b in enumerate(script_blocks):
                if b.get("id") == target_name:
                    current_block_idx = idx
                    break
            
            if current_block_idx is None:
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": f"Block {target_name} not found in project script",
                }

            # Calculate cumulative duration of previous blocks
            start_time_sec = 0.0
            for i in range(current_block_idx):
                prev_block = script_blocks[i]
                # Try to get duration from audio_generation
                audio_gen = prev_block.get("audio_generation")
                if audio_gen and isinstance(audio_gen, dict) and audio_gen.get("ok"):
                    prev_duration_ms = audio_gen.get("meta", {}).get("total_duration", 0)
                    start_time_sec += prev_duration_ms / 1000.0
                elif audio_gen and hasattr(audio_gen, 'ok') and audio_gen.ok:
                    prev_duration_ms = audio_gen.meta.get("total_duration", 0)
                    start_time_sec += prev_duration_ms / 1000.0

            # Get background video duration
            bg_video_duration = _get_video_duration_sec(bg_video)
            
            # Check if we have enough video
            end_time_sec = start_time_sec + duration_sec
            if end_time_sec > bg_video_duration:
                # Loop back to start if we exceed video length
                print(f"[extract] ⚠️  Requested segment ({start_time_sec:.2f}s-{end_time_sec:.2f}s) exceeds video length ({bg_video_duration:.2f}s)")
                print(f"[extract] → Wrapping to start of video")
                # Use modulo to wrap around
                start_time_sec = start_time_sec % bg_video_duration
                end_time_sec = start_time_sec + duration_sec
                # If still exceeds, just use what's available
                if end_time_sec > bg_video_duration:
                    end_time_sec = bg_video_duration
                    duration_sec = end_time_sec - start_time_sec
                    print(f"[extract] → Adjusted to {start_time_sec:.2f}s-{end_time_sec:.2f}s")

            # Create output directory
            video_dir = project_dir / "video"
            video_dir.mkdir(parents=True, exist_ok=True)
            output_path = video_dir / f"{target_name}.mp4"

            # Extract segment using ffmpeg
            # Use -ss before -i for faster seeking (input seeking)
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time_sec),
                "-i", str(bg_video),
                "-t", str(duration_sec),
                "-c", "copy",  # Use copy to avoid re-encoding (faster)
                str(output_path)
            ]

            if not _run_ffmpeg(cmd):
                # If copy fails (e.g., keyframe issues), try with re-encoding
                print("[extract] ⚠️  Copy mode failed, trying with re-encoding...")
                
                # Get original video resolution to maintain quality
                orig_width, orig_height = _get_video_resolution(bg_video)
                print(f"[extract] 📐 Original resolution: {orig_width}x{orig_height}")
                
                # Re-encode with high quality settings, maintaining original resolution
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time_sec),
                    "-i", str(bg_video),
                    "-t", str(duration_sec),
                    "-vf", f"scale={orig_width}:{orig_height}",  # Maintain original resolution
                    "-c:v", "libx264",
                    "-preset", "slow",  # Higher quality encoding (slower but better)
                    "-crf", "18",  # High quality (lower = better quality, 18 is visually lossless)
                    "-pix_fmt", "yuv420p",  # Ensure compatibility
                    "-c:a", "aac",
                    "-b:a", "192k",  # High quality audio bitrate
                    str(output_path)
                ]
                if not _run_ffmpeg(cmd):
                    return {
                        "ok": False,
                        "artifacts": [],
                        "meta": {},
                        "error": "Failed to extract video segment with ffmpeg",
                    }

            # Verify output exists and get actual duration
            if not output_path.exists():
                return {
                    "ok": False,
                    "artifacts": [],
                    "meta": {},
                    "error": f"Output file was not created: {output_path}",
                }

            actual_duration = _get_video_duration_sec(output_path)
            print(f"[extract] ✅ Extracted segment: {output_path} ({actual_duration:.2f}s)")

            meta = {
                "project": project,
                "target_name": target_name,
                "output_path": str(output_path),
                "start_time_sec": start_time_sec,
                "duration_sec": duration_sec,
                "actual_duration_sec": actual_duration,
                "source_video": str(bg_video),
            }

            return {
                "ok": True,
                "artifacts": [str(output_path)],
                "meta": meta,
                "error": None,
            }

        except Exception as e:
            print(f"[extract] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ok": False,
                "artifacts": [],
                "meta": {},
                "error": str(e),
            }

