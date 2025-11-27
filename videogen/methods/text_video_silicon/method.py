from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from dacite import from_dict

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.methods.text_video_silicon.constants import (
    SILICONFLOW_API_TOKEN, TEXT_TO_VIDEO_MODEL, STATUS_SUBMITTED, 
    NON_TERMINAL, STATUS_ERROR, STATUS_SUCCEED, FORMATS
)
from .sf_api import submit_video, download_to, check_status
from videogen.llm_engine import get_engine
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.action_spec import ActionSpec
from videogen.schema.generation_result_schema import GenerationResult
from videogen.schema.schema_registry import get_schema
from videogen.pipeline.path_utils import get_action_output_dir, get_output_file_path


@register_method
class TextVideoSilicon(BaseMethod):
    NAME = "text_video"
    OUTPUT_KIND = "video"

    def __init__(self) -> None:
        super().__init__()

    def generate_prompt(self, text: str, global_context: str | None = None) -> str:
        """
        Convert a line of dialogue into a vivid cinematic scene prompt for text-to-video models.
        """
        engine = get_engine()

        system_prompt = (
            "You are an expert cinematic visual director who converts dialogue lines "
            "into vivid scene descriptions for text-to-video generation models like Sora or Runway.\n"
            "Focus only on what the camera would show: the environment, lighting, motion, and atmosphere.\n"
            "Do not describe sound, dialogue, or voice-over. Your output must feel cinematic and visual.\n\n"
            "=== EXAMPLE ===\n\n"
            "Input line:\n"
            "\"This is the moment when the meteor struck the Earth.\"\n\n"
            "Output:\n"
            "A blazing meteor streaks through the night sky, leaving a trail of fire and smoke. "
            "The camera follows it in slow motion as it descends toward a vast desert landscape. "
            "Upon impact, a shockwave of light and dust erupts into the air, illuminating the horizon in orange and white. "
            "=== END OF EXAMPLE ===\n"
            "Now generate a similar cinematic description for the following line."
        )

        context_block = f"\nGlobal context for the video: {global_context.strip()}" if global_context else ""

        user_prompt = (
            f"Input line:\n{text.strip()}{context_block}\n\n"
            "Output:"
        )

        res = engine.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=400,
        )

        content = res["content"].strip()
        prompt = "\n".join(
            l for l in content.splitlines() if not l.strip().lower().startswith("title:")
        ).strip()

        return prompt

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for video generation.
        Does NOT execute heavy work - just creates and saves the block.
        """
        # Create WorkingBlock
        working_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        
        working_block = WorkingBlock(
            id=working_id,
            project_name=spec.config.get("project_name", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],  # Will be set by Pipeline
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
            modify_time=now
        )
        
        return working_block

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        """
        Execute video generation (async - may run multiple times).
        First call: generates prompt if needed, submits video request.
        Subsequent calls: polls status and downloads video when ready.
        """
        try:
            # Load config from config_json
            config_dict = json.loads(wb.config_json)
            schema_class = get_schema(self.NAME)
            config = from_dict(schema_class, config_dict)
            
            if not SILICONFLOW_API_TOKEN:
                error_msg = "Missing SILICONFLOW_API_TOKEN"
                wb.status = WorkingBlockStatus.ERROR
                result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error
                })
                return result
            
            # Check if we have a request_id from previous poll
            request_id = config_dict.get("request_id")
            
            if not request_id:
                # First poll - generate prompt if needed, then submit the video generation request
                
                # Generate prompt if not provided
                if not config.prompt:
                    config.prompt = self.generate_prompt(config.text, config.global_context)
                    config_dict["prompt"] = config.prompt
                
                # Get video format from project config
                project_name = wb.project_name or config_dict.get("project_name", "default")
                workdir = Path(config_dict.get("workdir", "."))
                project_config_path = workdir / "project" / project_name / f"{project_name}.json"
                video_format = "landscape"  # default
                image_size = "1280x720"  # default
                
                if project_config_path.exists():
                    try:
                        with open(project_config_path, 'r', encoding='utf-8') as f:
                            project_config = json.load(f)
                            video_format = project_config.get("size", "landscape")
                            image_size = FORMATS.get(video_format, "1280x720")
                    except Exception as e:
                        print(f"[TextVideoSilicon] Warning: Could not read project config: {e}")
                
                # Submit video generation request
                request_id = submit_video(config.prompt, image_size)
                
                if not request_id:
                    error_msg = "Failed to submit video generation request"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error
                    })
                    return result
                
                # Store request_id and updated config for next poll
                config_dict["request_id"] = request_id
                config_dict["image_size"] = image_size
                wb.config_json = json.dumps(config_dict)
                print(f"[TextVideoSilicon] ✅ Video submitted, requestId: {request_id}")
                
                # Return result to indicate still processing
                result = GenerationResult(status=WorkingBlockStatus.PENDING, output_path=None, duration_sec=None, error=None)
                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                    "request_id": request_id,
                    "status_detail": STATUS_SUBMITTED
                })
                return result
            
            # Subsequent polls - check status
            resp = check_status(request_id)
            new_status = resp.get("status") or STATUS_ERROR
            
            print(f"[TextVideoSilicon] Checking status for {wb.id}: {new_status}")
            
            if new_status == STATUS_SUCCEED:
                # Video is ready - download it
                videos = (resp.get("results") or {}).get("videos") or []
                url = videos[0].get("url") if videos else None
                
                if not url:
                    error_msg = "Video generation succeeded but no video URL in response"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error
                    })
                    return result
                
                print(f"[TextVideoSilicon] ✅ Task {request_id} succeeded, downloading video from {url}")
                
                # Get action output directory using new path structure
                workdir = Path(config_dict.get("workdir", "."))
                project_root = workdir.resolve()
                project_name = wb.project_name or config_dict.get("project_name", "default")
                block_id = wb.block_id or config_dict.get("target_name", wb.id)
                action_dir = get_action_output_dir(
                    project_root=project_root,
                    project_name=project_name,
                    block_id=block_id,
                    method_name=wb.method_name,
                    working_block_id=wb.id
                )
                action_dir.mkdir(parents=True, exist_ok=True)
                
                # Get output file path
                output_path = get_output_file_path(action_dir, "mp4")
                
                try:
                    # Download video
                    download_to(url, output_path)
                    print(f"[TextVideoSilicon] Saved video file: {output_path}")
                    
                    # Get video duration
                    cmd = [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(output_path)
                    ]
                    result_probe = subprocess.run(cmd, capture_output=True, text=True)
                    try:
                        duration_sec = float(result_probe.stdout.strip())
                    except Exception:
                        duration_sec = None
                    
                    # Update WorkingBlock
                    wb.status = WorkingBlockStatus.SUCCESS
                    wb.output_path = str(output_path)
                    
                    result = GenerationResult(
                        status=WorkingBlockStatus.SUCCESS,
                        output_path=str(output_path),
                        duration_sec=duration_sec,
                        error=None
                    )
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error,
                        "request_id": request_id,
                        "model": TEXT_TO_VIDEO_MODEL,
                        "prompt": config.prompt,
                        "source_url": url
                    })
                    
                    return result
                    
                except Exception as e:
                    error_msg = f"Download error: {e}"
                    print(f"[TextVideoSilicon] ❌ {error_msg}")
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error
                    })
                    return result
            
            elif new_status in NON_TERMINAL:
                # Still processing
                print(f"[TextVideoSilicon] Task {request_id} still processing: {new_status}")
                result = GenerationResult(status=WorkingBlockStatus.PENDING, output_path=None, duration_sec=None, error=None)
                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                    "request_id": request_id,
                    "status_detail": new_status
                })
                return result
            
            else:
                # Error or failed status → automatically retry by re-submitting
                error_msg = resp.get("error", f"Unknown error: {new_status}")
                print(f"[TextVideoSilicon] ❌ Task failed: {error_msg}")

                # ====== AUTO RETRY LOGIC ======
                config_dict.pop("request_id", None)
                wb.config_json = json.dumps(config_dict)

                # Reset status to PENDING to trigger re-submit
                wb.status = WorkingBlockStatus.PENDING

                result = GenerationResult(
                    status=WorkingBlockStatus.PENDING,
                    output_path=None,
                    duration_sec=None,
                    error=f"AutoRetry: {error_msg}"
                )

                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                    "status_detail": "auto_retry"
                })

                return result
                
        except Exception as e:
            error_msg = f"Status check error: {e}"
            print(f"[TextVideoSilicon] ❌ {error_msg}")
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
