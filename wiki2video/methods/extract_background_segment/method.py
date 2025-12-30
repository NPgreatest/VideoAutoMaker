#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, UTC
from dacite import from_dict

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.methods.base import BaseMethod
from wiki2video.methods.registry import register_method
from wiki2video.methods.extract_background_segment.schema import ExtractBackgroundSegmentSchema
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.core.paths import get_project_json_path
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult
from wiki2video.schema.schema_registry import get_schema
from wiki2video.core.utils import read_json
from wiki2video.core.path_utils import get_action_output_dir, get_output_file_path


def _run_ffmpeg(cmd: list[str]) -> bool:
    """
    Execute FFmpeg command without GBK decoding issues on Windows.
    Use raw bytes -> decode UTF-8 manually -> avoid UnicodeDecodeError.
    """
    print(f"[ffmpeg] {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False  # IMPORTANT: don't auto-decode using GBK
    )
    out, err = proc.communicate()

    # FFmpeg outputs UTF-8 on all platforms
    out = out.decode("utf-8", errors="ignore")
    err = err.decode("utf-8", errors="ignore")

    if proc.returncode != 0:
        print("[ffmpeg] ❌ FFmpeg failed:")
        print(err[-400:])  # show the last part for readability
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

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for background video extraction.
        Does NOT execute heavy work - just creates and saves the block.
        """

        # Create WorkingBlock
        working_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"
        
        spec.config = spec.config or {}
        spec.config.setdefault("project_id", "default")

        working_block = WorkingBlock(
            id=working_id,
            project_id=spec.config.get("project_id", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],  # Will be set by Pipeline
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
        )
        
        return working_block

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        """
        Execute background video segment extraction.
        This is a synchronous operation - completes in one call.
        """
        try:
            # Load config from config_json
            config_dict = json.loads(wb.config_json)
            schema_class = get_schema(self.NAME)
            config = from_dict(schema_class, config_dict)
            
            # Get project info (still need project.json for background_video path)
            project_id = wb.project_id
            project_json_path = get_project_json_path(project_id)

            if not project_json_path.exists():
                raise FileNotFoundError(f"Project {project_id} not found")
            
            # Read project JSON to get background_video path
            project_data = read_json(project_json_path)
            background_video_path = project_data.get("background_video")
            
            if not background_video_path:
                error_msg = "No background_video specified in project"
                result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                wb.status = WorkingBlockStatus.ERROR
                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error
                })
                return result
            
            # Resolve background video path
            bg_video = Path(background_video_path)
            if not bg_video.is_absolute():
                project_root = Path.cwd()
                bg_video = (project_root / bg_video).resolve()
            
            if not bg_video.exists():
                raise FileNotFoundError(f"Background Video {bg_video} not found")


            dao = WorkingBlockDAO()
            start_time_sec = 0
            duration_sec = None
            for prev_id in wb.prev_ids:
                prev_working_block = dao.get_by_id(prev_id)
                if prev_working_block and prev_working_block.method_name == "text_audio" and prev_working_block.status == WorkingBlockStatus.SUCCESS:
                    start_time_sec = prev_working_block.accumulated_duration_sec
                    result_data = json.loads(prev_working_block.result_json or "{}")
                    duration_sec = result_data.get("duration_sec")
                    wb.accumulated_duration_sec = prev_working_block.accumulated_duration_sec


            if duration_sec is None:
                raise Exception("No duration_sec specified")

            # Get background video duration
            bg_video_duration = _get_video_duration_sec(bg_video)
            
            # Check if we have enough video
            end_time_sec = start_time_sec + duration_sec
            if end_time_sec > bg_video_duration:
                # Loop back to start if we exceed video length
                print(f"[extract] ⚠️  Requested segment ({start_time_sec:.2f}s-{end_time_sec:.2f}s) exceeds video length ({bg_video_duration:.2f}s)")
                print(f"[extract] → Wrapping to start of video")
                start_time_sec = start_time_sec % bg_video_duration
                end_time_sec = start_time_sec + duration_sec
                if end_time_sec > bg_video_duration:
                    end_time_sec = bg_video_duration
                    duration_sec = end_time_sec - start_time_sec
                    print(f"[extract] → Adjusted to {start_time_sec:.2f}s-{end_time_sec:.2f}s")
            
            # Get action output directory using new path structure
            block_id = wb.block_id or config_dict.get("target_name", wb.id)
            action_dir = get_action_output_dir(
                project_id=project_id,
                block_id=block_id,
                method_name=wb.method_name,
                working_block_id=wb.id
            )
            
            # Get output file path
            output_path = get_output_file_path(action_dir, block_id, "mp4")
            
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
                print("[extract] ⚠️  Copy mode failed ...")
                raise Exception("ffmpeg failed")

            
            actual_duration = _get_video_duration_sec(output_path)
            print(f"[extract] ✅ Extracted segment: {output_path} ({actual_duration:.2f}s)")
            
            # Update WorkingBlock
            wb.status = WorkingBlockStatus.SUCCESS
            wb.output_path = str(output_path)

            result = GenerationResult(
                status=WorkingBlockStatus.SUCCESS,
                output_path=str(output_path),
                duration_sec=actual_duration,
                error=None
            )
            wb.result_json = json.dumps({
                "duration_sec": actual_duration,
                "error": None,
                "start_time_sec": start_time_sec,
                "source_video": str(bg_video)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
            print(f"[extract] ❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            wb.status = WorkingBlockStatus.ERROR
            result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
            wb.result_json = json.dumps({
                "status": result.status.value,
                "output_path": result.output_path,
                "duration_sec": result.duration_sec,
                "error": result.error
            })
            return result
