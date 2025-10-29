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

from videogen.methods.base import BaseMethod
from videogen.pipeline.schema import WorkingBlock, ScriptBlock
from videogen.methods.registry import register_method


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
    
    def process_working_block(self, working_block: WorkingBlock) -> bool:
        """
        Process a WorkingBlock using Remotion method.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not working_block.block:
            print(f"[RemotionMethod] WorkingBlock {working_block.working_id} has no block data")
            return False
        
        block = working_block.block
        
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
        
        # Handle image file integration
        image_filename = None
        injected_image_path = None
        if hasattr(block, 'extra_info') and block.extra_info:
            single_picture = block.extra_info.get("single_picture")
            if single_picture:
                image_filename = single_picture
                print(f"[RemotionMethod] Found single_picture: {image_filename}")
        
        # Calculate duration
        duration_ms = None
        if hasattr(block, 'audio_generation') and block.audio_generation and block.audio_generation.ok:
            duration_ms = block.audio_generation.meta.get('total_duration')
        
        # Create output directories
        output_folder = Path(working_block.output_folder) if working_block.output_folder else Path(".")
        project_dir = output_folder / "project" / working_block.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        video_dir = project_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_filename = f"{block.id}.mp4"
        output_path = video_dir / output_filename
        
        # Handle image file injection if single_picture is specified
        if image_filename:
            # Find the remotion_project directory
            method_dir = Path(__file__).parent
            remotion_project_path = method_dir / "remotion_project"
            if not remotion_project_path.exists():
                remotion_project_path = Path("remotion_project")
            
            # Create assets directory if it doesn't exist
            assets_dir = remotion_project_path / "public" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
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
        
        # Parse text to extract title and description
        if "|" in block.text:
            parts = block.text.split("|", 1)
            title = parts[0].strip()
            description = parts[1].strip()
        else:
            title = block.text.strip()
            description = ""
        
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
            "titleStartTime": int(duration_sec * 0.5 * 1000),  # Start at 50% of duration
            "soundEffect": self.DEFAULT_SOUND_EFFECT
        }
        
        # Save props to JSON file for debugging
        props_path = project_dir / f"{block.id}_props.json"
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
                    
                    # Update the block's video generation result
                    from videogen.pipeline.schema import GenerationResult
                    block.video_generation = GenerationResult(
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
                            "props_path": str(props_path)
                        },
                        error=None,
                    )
                    block.status = "done"
                    
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
                
                # Update the block's video generation result with error
                from videogen.pipeline.schema import GenerationResult
                block.video_generation = GenerationResult(
                    ok=False,
                    artifacts=[str(props_path)],
                    meta={},
                    error=error_msg,
                )
                block.status = "error"
                
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
            
            # Update the block's video generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.video_generation = GenerationResult(
                ok=False,
                artifacts=[str(props_path)],
                meta={},
                error=error_msg,
            )
            block.status = "error"
            
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
            
            # Update the block's video generation result with error
            from videogen.pipeline.schema import GenerationResult
            block.video_generation = GenerationResult(
                ok=False,
                artifacts=[str(props_path)],
                meta={},
                error=error_msg,
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
        block: Optional[ScriptBlock] = None,
    ) -> Dict[str, Any]:
        """
        Create a WorkingBlock for video generation using Remotion templates.
        The actual processing will be done by the global worker.
        
        Args:
            prompt: The prompt for video generation
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
        template_name = None
        if block and isinstance(block, dict):
            template_name = block.get("template")
        elif block and isinstance(block, str):
            template_name = block
        elif block and hasattr(block, 'extra_info') and block.extra_info:
            template_name = block.extra_info.get("template")
        
        # If no template specified, default to desktop
        if not template_name:
            template_name = "FilterDesktopSlide"
        
        # Validate template
        if template_name not in self.TEMPLATES:
            available_templates = list(self.TEMPLATES.keys())
            return {
                "ok": False, 
                "error": f"Invalid template '{template_name}'. Available templates: {available_templates}"
            }

        # Update block with template info
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
                "template": template_name,
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
