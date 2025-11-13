#!/usr/bin/env python3
"""
Remotion Method - Video Generation using Remotion templates
Follows the BaseMethod API for video generation
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import os

from videogen.methods.base import BaseMethod
from videogen.pipeline.schema import WorkingBlock, ScriptBlock
from videogen.methods.registry import register_method
from videogen.pipeline.utils import read_json, write_json


@register_method
class RemotionMethod(BaseMethod):
    NAME = "remotion_picture"
    OUTPUT_KIND = "video"

    # Available templates and their configurations
    TEMPLATES = {
        "FilterDesktopSlide": {
            "width": 1920,
            "height": 1080,
            "description": "Desktop format (16:9) with centered image and text overlay"
        },
        "FilterTikTokSlide": {
            "width": 1080,
            "height": 1920,
            "description": "TikTok format (9:16) with centered image and text overlay"
        }
    }

    DEFAULT_DURATION_SEC = 5
    DEFAULT_IMAGE = "openai.png"
    DEFAULT_SOUND_EFFECT = "dong_effect.wav"

    def supports_background_processing(self) -> bool:
        """Remotion method supports background processing."""
        return True
    
    def process_working_block(self, working_block: WorkingBlock) -> Optional[bool]:
        """
        Process a WorkingBlock using Remotion method.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful, False if failed
            None: if video_generation doesn't exist yet (keep pending)
        """
        if not working_block.block:
            print(f"[RemotionMethod] WorkingBlock {working_block.working_id} has no block data")
            return False
        
        # Load the latest block data from JSON file instead of using the stored block
        # This ensures we have the most up-to-date video_generation information
        try:
            output_folder = Path(working_block.output_folder) if working_block.output_folder else Path(".")
            json_path = output_folder / "project" / working_block.project_id / f"{working_block.project_id}.json"
            
            if json_path.exists():
                raw = read_json(json_path)
                script_blocks = raw.get("script", [])
                
                # Find the block with matching ID
                block_id = working_block.block.id
                block_dict = None
                for b in script_blocks:
                    if b.get("id") == block_id:
                        block_dict = b
                        break
                
                if block_dict:
                    from dacite import from_dict
                    block = from_dict(ScriptBlock, block_dict)
                else:
                    block = working_block.block
            else:
                block = working_block.block
        except Exception as e:
            print(f"[RemotionMethod] Error loading block from JSON: {e}, using stored block data")
            block = working_block.block
        
        # Check if video_generation exists and is ready (prior job finished)
        video_gen = block.video_generation
        if not video_gen:
            print(f"[RemotionMethod] Video generation not ready yet for {block.id}, keeping pending")
            return None
        
        # Handle both GenerationResult object and dict cases
        if hasattr(video_gen, 'ok'):
            is_ok = video_gen.ok
            meta = video_gen.meta
        else:
            is_ok = video_gen.get('ok', False)
            meta = video_gen.get('meta', {})
        
        # Get video path from video_generation meta
        video_path_str = meta.get('output_path') if meta else None
        video_path = Path(video_path_str) if video_path_str else None
        
        # If prior job didn't finish, still waiting
        if not is_ok or not video_path_str or not video_path or not video_path.exists():
            print(f"[RemotionMethod] Video generation not ready yet for {block.id}, keeping pending")
            return None
        
        # Get image path and title from extra_info
        image_filename = None
        title = ""
        if hasattr(block, 'extra_info') and block.extra_info:
            image_filename = block.extra_info.get("single_picture")
            title = block.extra_info.get("title", "")
        
        # If no title in extra_info, fall back to block.text
        if not title:
            if "|" in block.text:
                parts = block.text.split("|", 1)
                title = parts[0].strip()
            else:
                title = block.text.strip()
        
        # Determine template from block parameter
        template_name = None
        if hasattr(block, 'extra_info') and block.extra_info:
            template_name = block.extra_info.get("template")
        
        # If no template specified, default to desktop
        if not template_name:
            template_name = "FilterDesktopSlide"
        
        # Validate template
        if template_name not in self.TEMPLATES:
            print(f"[RemotionMethod] Invalid template '{template_name}'")
            return False
        
        # Calculate duration from video or audio
        duration_ms = None
        if hasattr(block, 'audio_generation') and block.audio_generation:
            # Handle both GenerationResult object and dict cases
            if hasattr(block.audio_generation, 'ok'):
                audio_ok = block.audio_generation.ok
                audio_meta = block.audio_generation.meta
            else:
                audio_ok = block.audio_generation.get('ok', False)
                audio_meta = block.audio_generation.get('meta', {})
            
            if audio_ok:
                duration_ms = audio_meta.get('total_duration')
        
        # Create output directories
        output_folder = Path(working_block.output_folder) if working_block.output_folder else Path(".")
        project_dir = output_folder / "project" / working_block.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        video_dir = project_dir / "remotion_video"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_filename = f"{block.id}.mp4"
        output_path = video_dir / output_filename
        
        # Find the remotion_project directory
        method_dir = Path(__file__).parent
        remotion_project_path = method_dir / "remotion_project"
        if not remotion_project_path.exists():
            remotion_project_path = Path("remotion_project")
        
        # Create assets directory if it doesn't exist
        assets_dir = remotion_project_path / "public" / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle image file injection if single_picture is specified
        injected_image_path = None
        if image_filename:
            # Source image path in project folder
            source_image_path = project_dir / image_filename
            
            # Destination image path in remotion assets
            injected_image_path = assets_dir / image_filename
            
            if source_image_path.exists():
                try:
                    # Copy image to remotion assets folder
                    shutil.copy2(str(source_image_path), str(injected_image_path))
                    print(f"[RemotionMethod] ✅ Copied image {image_filename} to remotion assets")
                except Exception as e:
                    print(f"[RemotionMethod] ❌ Failed to copy image {image_filename}: {str(e)}")
                    image_filename = None  # Fall back to default image
            else:
                print(f"[RemotionMethod] ❌ Image file not found: {source_image_path}")
                image_filename = None  # Fall back to default image
        
        # Copy video to remotion assets if needed
        # We'll pass the video path as a prop, but we need to make it accessible
        # For now, we'll copy it to assets or use absolute path
        video_filename = f"{block.id}_video.mp4"
        injected_video_path = assets_dir / video_filename
        try:
            shutil.copy2(str(video_path), str(injected_video_path))
            print(f"[RemotionMethod] ✅ Copied video to remotion assets")
        except Exception as e:
            print(f"[RemotionMethod] ❌ Failed to copy video: {str(e)}")
            return False
        
        description = ""  # Description can be empty or from extra_info
        if hasattr(block, 'extra_info') and block.extra_info:
            description = block.extra_info.get("description", "")
        
        # Calculate duration
        duration_sec = (duration_ms / 1000.0) if duration_ms else self.DEFAULT_DURATION_SEC
        
        # Ensure duration is within reasonable bounds
        if duration_sec < 3:
            duration_sec = 3
        elif duration_sec > 10:
            duration_sec = 10
        
        # Create props for Remotion
        props = {
            "title": title,
            "description": description,
            "duration": duration_sec,
            "imagePath": image_filename if image_filename else self.DEFAULT_IMAGE,
            "videoPath": video_filename,  # Video file in assets folder
            "titleStartTime": int(duration_sec * 0.5 * 1000),  # Start at 50% of duration
            "soundEffect": self.DEFAULT_SOUND_EFFECT
        }
        
        # Save props to JSON file for debugging
        props_path = project_dir / "remotion_video" / f"{block.id}_props.json"
        with open(props_path, 'w', encoding='utf-8') as f:
            json.dump(props, f, indent=2)
        
        try:
            # Find the remotion_project directory - it's located in the same directory as this method
            method_dir = Path(__file__).parent
            remotion_project_path = method_dir / "remotion_project"
            if not remotion_project_path.exists():
                # If not found, try relative to the current working directory
                remotion_project_path = Path("remotion_project")
            
            # Use a temporary filename in remotion's output directory
            temp_output_filename = f"temp_{block.id}.mp4"
            temp_output_path = remotion_project_path / "output" / temp_output_filename
            # For the command, use a relative path from the remotion_project directory
            temp_output_path_for_cmd = Path("output") / temp_output_filename
            
            # Render video using Remotion
            cmd = [
                "npx", "remotion", "render",
                template_name,
                str(temp_output_path_for_cmd),
                "--props", json.dumps(props)
            ]
            
            print(f"[RemotionMethod] 🎬 Rendering {template_name} video for {block.id}...")
            print(f"[RemotionMethod] 📊 Props: {json.dumps(props, indent=2)}")
            print(f"[RemotionMethod] 📁 Output: {output_path}")
            
            result = subprocess.run(
                cmd, 
                cwd=remotion_project_path, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Move the video from temp location to final destination
                if temp_output_path.exists():
                    shutil.move(str(temp_output_path), str(output_path))
                    print(f"[RemotionMethod] ✅ Video generated and moved successfully!")
                    
                    # Clean up injected image file if it exists
                    if injected_image_path and injected_image_path.exists():
                        try:
                            injected_image_path.unlink()
                            print(f"[RemotionMethod] 🗑️ Cleaned up injected image: {image_filename}")
                        except Exception as e:
                            print(f"[RemotionMethod] ⚠️ Failed to clean up image {image_filename}: {str(e)}")
                    
                    # Update the block's remotion_generation result
                    from videogen.pipeline.schema import GenerationResult
                    block.remotion_generation = GenerationResult(
                        ok=True,
                        artifacts=[str(output_path), str(props_path)],
                        meta={
                            "template": template_name,
                            "template_config": self.TEMPLATES[template_name],
                            "duration_sec": duration_sec,
                            "title": title,
                            "description": description,
                            "props": props,
                            "output_path": str(output_path),
                            "props_path": str(props_path),
                            "source_video_path": str(video_path),
                            "status": "done"
                        },
                        error=None,
                    )
                    block.status = "done"
                    
                    # Clean up copied video file
                    if injected_video_path.exists():
                        try:
                            injected_video_path.unlink()
                            print(f"[RemotionMethod] 🗑️ Cleaned up copied video: {video_filename}")
                        except Exception as e:
                            print(f"[RemotionMethod] ⚠️ Failed to clean up video {video_filename}: {str(e)}")
                    
                    # Save updated block to JSON file
                    self._save_block_to_json(working_block, block)
                    
                    return True
                else:
                    print(f"[RemotionMethod] ❌ Video file not found at {temp_output_path}")
                    # Clean up injected image file if it exists
                    if injected_image_path and injected_image_path.exists():
                        try:
                            injected_image_path.unlink()
                            print(f"[RemotionMethod] 🗑️ Cleaned up injected image: {image_filename}")
                        except Exception as e:
                            print(f"[RemotionMethod] ⚠️ Failed to clean up image {image_filename}: {str(e)}")
                    # Clean up copied video file
                    if injected_video_path.exists():
                        try:
                            injected_video_path.unlink()
                            print(f"[RemotionMethod] 🗑️ Cleaned up copied video: {video_filename}")
                        except Exception as e:
                            print(f"[RemotionMethod] ⚠️ Failed to clean up video {video_filename}: {str(e)}")
                    return False
            else:
                error_msg = f"Remotion rendering failed: {result.stderr}"
                print(f"[RemotionMethod] ❌ {error_msg}")
                
                # Clean up injected image file if it exists
                if injected_image_path and injected_image_path.exists():
                    try:
                        injected_image_path.unlink()
                        print(f"[RemotionMethod] 🗑️ Cleaned up injected image: {image_filename}")
                    except Exception as e:
                        print(f"[RemotionMethod] ⚠️ Failed to clean up image {image_filename}: {str(e)}")
                
                # Update the block's remotion_generation result with error
                from videogen.pipeline.schema import GenerationResult
                block.remotion_generation = GenerationResult(
                    ok=False,
                    artifacts=[str(props_path)],
                    meta={
                        "status": "error"
                    },
                    error=error_msg,
                )
                block.status = "error"
                
                # Clean up copied video file
                if injected_video_path.exists():
                    try:
                        injected_video_path.unlink()
                        print(f"[RemotionMethod] 🗑️ Cleaned up copied video: {video_filename}")
                    except Exception as e:
                        print(f"[RemotionMethod] ⚠️ Failed to clean up video {video_filename}: {str(e)}")
                
                # Save updated block to JSON file
                self._save_block_to_json(working_block, block)
                
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Remotion rendering timed out (5 minutes)"
            print(f"[RemotionMethod] ❌ {error_msg}")
            
            # Clean up injected image file if it exists
            if injected_image_path and injected_image_path.exists():
                try:
                    injected_image_path.unlink()
                    print(f"[RemotionMethod] 🗑️ Cleaned up injected image: {image_filename}")
                except Exception as e:
                    print(f"[RemotionMethod] ⚠️ Failed to clean up image {image_filename}: {str(e)}")
            
            # Clean up copied video file
            if injected_video_path.exists():
                try:
                    injected_video_path.unlink()
                    print(f"[RemotionMethod] 🗑️ Cleaned up copied video: {video_filename}")
                except Exception as e:
                    print(f"[RemotionMethod] ⚠️ Failed to clean up video {video_filename}: {str(e)}")
            
            # Update the block's remotion_generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.remotion_generation = GenerationResult(
                ok=False,
                artifacts=[str(props_path)],
                meta={
                    "status": "error"
                },
                error=error_msg,
            )
            block.status = "error"
            
            # Save updated block to JSON file
            self._save_block_to_json(working_block, block)
            
            return False
        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            print(f"[RemotionMethod] ❌ {error_msg}")
            
            # Clean up injected image file if it exists
            if injected_image_path and injected_image_path.exists():
                try:
                    injected_image_path.unlink()
                    print(f"[RemotionMethod] 🗑️ Cleaned up injected image: {image_filename}")
                except Exception as cleanup_e:
                    print(f"[RemotionMethod] ⚠️ Failed to clean up image {image_filename}: {str(cleanup_e)}")
            
            # Clean up copied video file
            if injected_video_path.exists():
                try:
                    injected_video_path.unlink()
                    print(f"[RemotionMethod] 🗑️ Cleaned up copied video: {video_filename}")
                except Exception as cleanup_e:
                    print(f"[RemotionMethod] ⚠️ Failed to clean up video {video_filename}: {str(cleanup_e)}")
            
            # Update the block's remotion_generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.remotion_generation = GenerationResult(
                ok=False,
                artifacts=[str(props_path)],
                meta={
                    "status": "error"
                },
                error=error_msg,
            )
            block.status = "error"
            
            # Save updated block to JSON file
            self._save_block_to_json(working_block, block)
            
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
                print(f"[RemotionMethod] ⚠️ JSON file not found: {json_path}, skipping save")
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
                print(f"[RemotionMethod] ⚠️ Block {block.id} not found in JSON file, skipping save")
                return
            
            # Update timestamp
            raw["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            
            # Write back to JSON file
            write_json(json_path, raw)
            print(f"[RemotionMethod] ✅ Saved block {block.id} to JSON: {json_path}")
            
        except Exception as e:
            print(f"[RemotionMethod] ⚠️ Error saving block to JSON: {e}")
            # Don't raise - this is a non-critical operation

    def run(
        self,
        *,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        """
        Create a WorkingBlock for video generation using Remotion templates.
        The actual processing will be done by the global worker.
        
        Args:
            project: Project name
            target_name: Target video name
            text: Text content for the video (can be title or description)
            workdir: Working directory
            duration_ms: Duration in milliseconds
            block: Template block information (should contain template name)
        """
        
        if not text.strip():
            return {"ok": False, "error": "text cannot be empty"}

        # Determine template from block parameter
        template_name = block.extra_info.get("template") or "FilterDesktopSlide"
        
        # Validate template
        if template_name not in self.TEMPLATES:
            available_templates = list(self.TEMPLATES.keys())
            return {
                "ok": False, 
                "error": f"Invalid template '{template_name}'. Available templates: {available_templates}"
            }

        # Update the block with template info
        if block:
            if not hasattr(block, 'extra_info') or block.extra_info is None:
                block.extra_info = {}
            block.extra_info["template"] = template_name

        # Create WorkingBlock using base method
        working_id = self.create_working_block(project, target_name, workdir, block)
        
        if not working_id:
            return {
                "ok": False,
                "error": f"Failed to create WorkingBlock for {target_name}"
            }
        
        print(f"📤 Remotion video generation queued for {target_name} (ID: {working_id})")
        print(f"   → Task will be processed by global worker")
        
        # Return immediately with submitted status
        return {
            "ok": True,  # Submission was successful
            "artifacts": [],
            "meta": {
                "working_id": working_id,
                "project": project,
                "target_name": target_name,
                "status": "submitted",
            },
            "error": None,
        }

    def generate_prompt(self, text: str) -> str:
        """
        Generate a prompt for video creation based on text content
        
        Args:
            text: Input text content
            
        Returns:
            Generated prompt for video creation
        """
        # Simple prompt generation - can be enhanced with LLM integration
        if "|" in text:
            title, description = text.split("|", 1)
            return f"Create a video with title '{title.strip()}' and description '{description.strip()}'"
        else:
            return f"Create a video with title '{text.strip()}'"
