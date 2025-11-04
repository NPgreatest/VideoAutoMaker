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
from videogen.llm_engine import get_engine
from videogen.pipeline.schema import WorkingBlock, ScriptBlock
from videogen.pipeline.utils import read_json, write_json
from datetime import datetime, timezone

@register_method
class TextVideoSilicon(BaseMethod):
    NAME = "text_video"
    OUTPUT_KIND = "video"

    def __init__(self) -> None:
        super().__init__()

    def supports_background_processing(self) -> bool:
        """Text Video Silicon method supports background processing."""
        return True
    
    def process_working_block(self, working_block: WorkingBlock) -> Optional[bool]:
        """
        Process a WorkingBlock using Text Video Silicon method.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful
            False: if failed with error
            None: if still processing (non-terminal state)
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
                self._save_block_to_json(working_block, block) # still save back
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
                
                main_mp4 = video_dir / f"{block.id}.mp4"
                
                try:
                    # Download video directly to main file
                    download_to(url, main_mp4)
                    print(f"[TextVideoSilicon] Saved video file: {main_mp4}")
                    
                    # Get original video duration for metadata
                    import subprocess
                    cmd = [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(main_mp4)
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    try:
                        original_dur = float(result.stdout.strip())
                    except Exception:
                        original_dur = 0.0
                    
                    # Update the block's video generation result
                    from videogen.pipeline.schema import GenerationResult
                    block.video_generation = GenerationResult(
                        ok=True,
                        artifacts=[str(main_mp4)],
                        meta={
                            "request_id": request_id,
                            "model": TEXT_TO_VIDEO_MODEL,
                            "prompt": block.prompt,
                            "source_url": url,
                            "duration": str(original_dur),
                            "output_path": str(main_mp4),
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
                        "duration": str(original_dur),
                        "output_path": str(main_mp4),
                        "created": time.time(),
                        "finished": time.time(),
                    }
                    meta_path = main_mp4.with_suffix(".meta.json")
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    print(f"[TextVideoSilicon] Meta saved: {meta_path}")
                    
                    # Save block back to JSON file
                    self._save_block_to_json(working_block, block)
                    
                    return True
                    
                except Exception as e:
                    print(f"[TextVideoSilicon] Download or resize error for {request_id}: {e}")
                    
                    # Preserve existing meta, especially request_id
                    existing_meta = {}
                    if block.video_generation:
                        video_gen = block.video_generation
                        if hasattr(video_gen, 'meta'):
                            existing_meta = dict(video_gen.meta) if isinstance(video_gen.meta, dict) else {}
                        elif isinstance(video_gen, dict):
                            existing_meta = dict(video_gen.get('meta', {})) if isinstance(video_gen.get('meta'), dict) else {}
                    
                    # Ensure request_id is preserved
                    if 'request_id' not in existing_meta and request_id:
                        existing_meta['request_id'] = request_id
                    
                    # Update the block's video generation result with an error
                    from videogen.pipeline.schema import GenerationResult
                    block.video_generation = GenerationResult(
                        ok=False,
                        artifacts=[],
                        meta=existing_meta,  # Preserve existing meta including request_id
                        error=f"Download error: {e}",
                    )
                    block.status = "error"
                    
                    # Save block back to JSON file (with error state)
                    self._save_block_to_json(working_block, block)
                    
                    return False
            
            elif new_status in NON_TERMINAL:
                # Still processing, not an error yet - keep as PENDING
                print(f"[TextVideoSilicon] Task {request_id} still processing: {new_status}")
                # Update status in meta to reflect current status
                from videogen.pipeline.schema import GenerationResult
                
                # Preserve existing meta, especially request_id
                meta = {}
                if block.video_generation:
                    video_gen = block.video_generation
                    if hasattr(video_gen, 'meta'):
                        meta = dict(video_gen.meta) if isinstance(video_gen.meta, dict) else {}
                    elif isinstance(video_gen, dict):
                        meta = dict(video_gen.get('meta', {})) if isinstance(video_gen.get('meta'), dict) else {}
                
                # Ensure request_id is always set
                if 'request_id' not in meta and request_id:
                    meta['request_id'] = request_id
                
                # Update status and timestamp
                meta['status'] = new_status
                meta['last_checked'] = time.time()
                
                block.video_generation = GenerationResult(
                    ok=True,  # Still in progress, submission was successful
                    artifacts=[],
                    meta=meta,  # Preserve existing meta including request_id
                    error=None,
                )
                return None  # Return None to indicate still processing
            
            else:
                # Error or other terminal state
                error_msg = resp.get("error", f"Unknown error: {new_status}")
                print(f"[TextVideoSilicon] Task {request_id} failed: {error_msg}")
                
                # Preserve existing meta, especially request_id
                existing_meta = {}
                if block.video_generation:
                    video_gen = block.video_generation
                    if hasattr(video_gen, 'meta'):
                        existing_meta = dict(video_gen.meta) if isinstance(video_gen.meta, dict) else {}
                    elif isinstance(video_gen, dict):
                        existing_meta = dict(video_gen.get('meta', {})) if isinstance(video_gen.get('meta'), dict) else {}
                
                # Ensure request_id is preserved
                if 'request_id' not in existing_meta and request_id:
                    existing_meta['request_id'] = request_id
                
                # Update status in meta
                existing_meta['status'] = new_status
                existing_meta['error_time'] = time.time()
                
                # Update the block's video generation result with error
                from videogen.pipeline.schema import GenerationResult
                block.video_generation = GenerationResult(
                    ok=False,
                    artifacts=[],
                    meta=existing_meta,  # Preserve existing meta including request_id
                    error=error_msg,
                )
                block.status = "error"
                
                return False
                
        except Exception as e:
            print(f"[TextVideoSilicon] Error checking status for {request_id}: {e}")
            
            # Preserve existing meta, especially request_id
            existing_meta = {}
            if block.video_generation:
                video_gen = block.video_generation
                if hasattr(video_gen, 'meta'):
                    existing_meta = dict(video_gen.meta) if isinstance(video_gen.meta, dict) else {}
                elif isinstance(video_gen, dict):
                    existing_meta = dict(video_gen.get('meta', {})) if isinstance(video_gen.get('meta'), dict) else {}
            
            # Ensure request_id is preserved (use the request_id variable if available)
            if 'request_id' not in existing_meta:
                if request_id:
                    existing_meta['request_id'] = request_id
                elif block.video_generation:
                    # Try to get from block if request_id variable is None
                    video_gen = block.video_generation
                    if hasattr(video_gen, 'meta') and isinstance(video_gen.meta, dict):
                        existing_meta['request_id'] = video_gen.meta.get('request_id')
                    elif isinstance(video_gen, dict):
                        existing_meta['request_id'] = video_gen.get('meta', {}).get('request_id')
            
            # Update the block's video generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.video_generation = GenerationResult(
                ok=False,
                artifacts=[],
                meta=existing_meta,  # Preserve existing meta including request_id
                error=f"Status check error: {e}",
            )
            block.status = "error"
            
            return False

    def _save_block_to_json(self, working_block: WorkingBlock, block: ScriptBlock) -> None:
        """
        Save the updated block back to the JSON file.
        
        Args:
            working_block: The WorkingBlock containing output_folder and project_id
            block: The updated ScriptBlock to save
        """
        try:
            # Construct JSON file path: workdir / "project" / project_id / f"{project_id}.json"
            output_folder = Path(working_block.output_folder) if working_block.output_folder else Path(".")
            json_path = output_folder / "project" / working_block.project_id / f"{working_block.project_id}.json"
            
            if not json_path.exists():
                print(f"[TextVideoSilicon] ⚠️ JSON file not found: {json_path}, skipping save")
                return
            
            # Read existing JSON
            raw = read_json(json_path)
            
            # Find and update the block
            updated = False
            for i, b in enumerate(raw.get("script", [])):
                if b.get("id") == block.id:
                    raw["script"][i] = block.to_dict()
                    updated = True
                    break
            
            if not updated:
                print(f"[TextVideoSilicon] ⚠️ Block {block.id} not found in JSON file, skipping save")
                return
            
            # Update timestamp
            raw["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            
            # Write back to JSON file
            write_json(json_path, raw)
            print(f"[TextVideoSilicon] ✅ Saved block {block.id} to JSON: {json_path}")
            
        except Exception as e:
            print(f"[TextVideoSilicon] ⚠️ Error saving block to JSON: {e}")
            # Don't raise - this is a non-critical operation
    
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
