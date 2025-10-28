from __future__ import annotations

import json
import os.path
import time
from pathlib import Path
from typing import Dict, Any, Optional

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.methods.text_video_silicon.constants import (
    SILICONFLOW_API_TOKEN, TEXT_TO_VIDEO_MODEL, STATUS_SUBMITTED, NON_TERMINAL, STATUS_ERROR, STATUS_SUCCEED
)
from .sf_api import submit_video, download_to, check_status
from .utils import resize_video_duration
from videogen.llm_engine import get_engine
from videogen.pipeline.schema import WorkingBlock, ScriptBlock

@register_method
class TextVideoSilicon(BaseMethod):
    NAME = "text_video"
    OUTPUT_KIND = "video"

    def __init__(self) -> None:
        super().__init__()

    def supports_background_processing(self) -> bool:
        """Text Video Silicon method supports background processing."""
        return True
    
    def process_working_block(self, working_block: WorkingBlock) -> bool:
        """
        Process a WorkingBlock using Text Video Silicon method.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not working_block.block:
            print(f"[TextVideoSilicon] WorkingBlock {working_block.working_id} has no block data")
            return False
        
        block = working_block.block
        
        if not SILICONFLOW_API_TOKEN:
            print(f"[TextVideoSilicon] Missing SILICONFLOW_API_TOKEN")
            return False
        
        # Check if already completed
        video_gen = block.video_generation
        if video_gen:
            # Handle both GenerationResult object and dict cases
            if hasattr(video_gen, 'ok'):
                # It's a GenerationResult object
                is_ok = video_gen.ok
                meta = video_gen.meta
            else:
                # It's a dictionary
                is_ok = video_gen.get('ok', False)
                meta = video_gen.get('meta', {})
            
            if (is_ok and 'request_id' in meta and 
                os.path.exists(meta.get('output_path', ''))):
                print(f"[TextVideoSilicon] Using existing completed video for {block.id}")
                return True
        
        # Get request_id from block's video generation meta
        request_id = None
        if block.video_generation:
            video_gen = block.video_generation
            if hasattr(video_gen, 'meta'):
                # It's a GenerationResult object
                meta = video_gen.meta
            else:
                # It's a dictionary
                meta = video_gen.get('meta', {})
            
            if 'request_id' in meta:
                request_id = meta['request_id']
        
        if not request_id:
            print(f"[TextVideoSilicon] No request_id found in block {block.id}")
            return False
        
        try:
            # Check status with SiliconFlow API
            resp = check_status(request_id)
            new_status = resp.get("status") or STATUS_ERROR
            
            print(f"[TextVideoSilicon] Checking status for {block.id}: {new_status}")
            
            # Handle success case
            if new_status == STATUS_SUCCEED:
                videos = (resp.get("results") or {}).get("videos") or []
                url = videos[0].get("url") if videos else None
                
                if not url:
                    print(f"[TextVideoSilicon] Succeed but no video url for {block.id}")
                    return False
                
                print(f"[TextVideoSilicon] ✅ Task {request_id} succeeded, downloading video from {url}")
                
                # Create output directories
                output_folder = Path(working_block.output_folder) if working_block.output_folder else Path(".")
                project_dir = output_folder / "project" / working_block.project_id
                video_dir = project_dir / "video"
                video_dir.mkdir(parents=True, exist_ok=True)
                
                final_mp4 = video_dir / f"{block.id}.mp4"
                raw_mp4 = video_dir / f"{block.id}_raw.mp4"
                
                try:
                    # Download raw (always keep this)
                    download_to(url, raw_mp4)
                    print(f"[TextVideoSilicon] Saved raw file: {raw_mp4}")
                    
                    # Resize to target duration, but keep raw
                    target_dur = None
                    if block.audio_generation:
                        audio_gen = block.audio_generation
                        if hasattr(audio_gen, 'ok') and audio_gen.ok:
                            # It's a GenerationResult object
                            target_dur = audio_gen.meta.get('total_duration', 5.0) / 1000.0
                        elif isinstance(audio_gen, dict) and audio_gen.get('ok', False):
                            # It's a dictionary
                            target_dur = audio_gen.get('meta', {}).get('total_duration', 5.0) / 1000.0
                        else:
                            target_dur = 5.0
                    else:
                        target_dur = 5.0
                    
                    new_dur = resize_video_duration(raw_mp4, final_mp4, target_dur)
                    
                    if new_dur > 0:
                        print(f"[TextVideoSilicon] Resized to {new_dur:.2f}s → {final_mp4.name}")
                    else:
                        print(f"[TextVideoSilicon] ⚠️ Resize failed, keeping raw as source only")
                    
                    # Update the block's video generation result
                    from videogen.pipeline.schema import GenerationResult
                    block.video_generation = GenerationResult(
                        ok=True,
                        artifacts=[str(final_mp4 if final_mp4.exists() else raw_mp4)],
                        meta={
                            "request_id": request_id,
                            "model": TEXT_TO_VIDEO_MODEL,
                            "prompt": block.prompt,
                            "source_url": url,
                            "duration": str(target_dur),
                            "output_path": str(final_mp4 if final_mp4.exists() else raw_mp4),
                            "finished": time.time(),
                        },
                        error=None,
                    )
                    block.status = "done"
                    
                    # Save metadata
                    meta = {
                        "request_id": request_id,
                        "model": TEXT_TO_VIDEO_MODEL,
                        "prompt": block.prompt,
                        "source_url": url,
                        "duration": str(target_dur),
                        "created": time.time(),
                        "finished": time.time(),
                    }
                    meta_path = final_mp4.with_suffix(".meta.json")
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    print(f"[TextVideoSilicon] Meta saved: {meta_path}")
                    
                    return True
                    
                except Exception as e:
                    print(f"[TextVideoSilicon] Download or resize error for {request_id}: {e}")
                    
                    # Update the block's video generation result with an error
                    from videogen.pipeline.schema import GenerationResult
                    block.video_generation = GenerationResult(
                        ok=False,
                        artifacts=[],
                        meta={},
                        error=f"Download/Resize error: {e}",
                    )
                    block.status = "error"
                    
                    return False
            
            elif new_status in NON_TERMINAL:
                # Still processing, not an error yet
                print(f"[TextVideoSilicon] Task {request_id} still processing: {new_status}")
                return False
            
            else:
                # Error or other terminal state
                error_msg = resp.get("error", f"Unknown error: {new_status}")
                print(f"[TextVideoSilicon] Task {request_id} failed: {error_msg}")
                
                # Update the block's video generation result with error
                from videogen.pipeline.schema import GenerationResult
                block.video_generation = GenerationResult(
                    ok=False,
                    artifacts=[],
                    meta={},
                    error=error_msg,
                )
                block.status = "error"
                
                return False
                
        except Exception as e:
            print(f"[TextVideoSilicon] Error checking status for {request_id}: {e}")
            
            # Update the block's video generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.video_generation = GenerationResult(
                ok=False,
                artifacts=[],
                meta={},
                error=f"Status check error: {e}",
            )
            block.status = "error"
            
            return False

    def run(
        self,
        *,
        prompt: str,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Optional[ScriptBlock] = None
    ) -> Dict[str, Any]:
        """
        Create a WorkingBlock for video generation using SiliconFlow API.
        The actual processing will be done by the global worker.
        """
        if not SILICONFLOW_API_TOKEN:
            return {"ok": False, "artifacts": [], "meta": {}, "error": "Missing SILICONFLOW_API_TOKEN."}

        # Check if already completed
        if block and block.video_generation and block.video_generation.ok and 'request_id' in block.video_generation.meta and os.path.exists(block.video_generation.meta['output_path']):
            request_id = block.video_generation.meta['request_id']
            print(f"→ Using existing completed video for {target_name}")
            return {
                "ok": True,
                "artifacts": [block.video_generation.meta['output_path']],
                "meta": block.video_generation.meta,
                "error": None,
            }

        # Get project configuration to determine video format
        project_config_path = workdir / "project" / project / f"{project}.json"
        video_format = "landscape"  # default
        image_size = "1280x720"  # default
        
        if project_config_path.exists():
            try:
                import json
                with open(project_config_path, 'r', encoding='utf-8') as f:
                    project_config = json.load(f)
                    video_format = project_config.get("size", "landscape")
                    # Map format to image size
                    from .constants import FORMATS
                    image_size = FORMATS.get(video_format, "1280x720")
            except Exception as e:
                print(f"[TextVideoSilicon] Warning: Could not read project config: {e}")

        # Submit new task
        request_id = submit_video(prompt, image_size)
        if not request_id:
            return {"ok": False, "artifacts": [], "meta": {}, "error": "Submit failed (no requestId)."}

        # Update block with request_id and set initial video generation result
        if block:
            # Set initial video generation result with submitted status
            from videogen.pipeline.schema import GenerationResult
            block.video_generation = GenerationResult(
                ok=True,  # Submission was successful
                artifacts=[],
                meta={
            "request_id": request_id,
            "project": project,
            "target_name": target_name,
            "status": STATUS_SUBMITTED,
                    "output_path": "",  # Will be filled by worker
            "source_url": "",
                    "submitted_at": str(time.time()),
                },
                error=None,
            )

        # Create WorkingBlock using base method
        working_id = self.create_working_block(project, target_name, workdir, block)
        
        if not working_id:
            return {
                "ok": False,
                "error": f"Failed to create WorkingBlock for {target_name}"
            }

        print(f"📤 Video generation submitted for {target_name} (ID: {request_id})")
        print(f"   → Task will be processed by global worker")
        
        # Return immediately with submitted status
        return {
            "ok": True,  # Submission was successful
            "artifacts": [],
            "meta": {
                "working_id": working_id,
                "request_id": request_id,
                "project": project,
                "target_name": target_name,
                "status": STATUS_SUBMITTED,
                "output_path": "",  # Will be filled by worker
                "source_url": "",
                "submitted_at": str(time.time()),
            },
            "error": None,
        }

    def generate_prompt(self, text: str) -> str:
        """
        Convert a line of dialogue into a vivid cinematic scene prompt for text-to-video models (e.g. Sora, Runway).
        Uses an English few-shot example to demonstrate desired style and structure.
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

        user_prompt = (
            f"Input line:\n{text.strip()}\n\n"
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
