#!/usr/bin/env python3
"""
Remotion Method - Video Generation using Remotion templates
Follows the BaseMethod API for video generation
"""

import abc
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional


class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override
    OUTPUT_KIND: str = "any"  # "audio" | "video" | "other"

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def run(self, *, prompt: str, project: str, target_name: str, text: str, workdir: Path, duration_ms: int | None = None, block) -> Dict[str, Any]:
        """Execute the method and return a dict:
        {
          "ok": bool,
          "artifacts": [<paths>],
          "meta": {...},
          "error": <str or None>
        }
        """
        raise NotImplementedError

    def generate_prompt(self, text: str) -> str:
        """Execute the method and return a str:
        prompt...
        """
        raise NotImplementedError


def register_method(cls):
    """Decorator to register a method class"""
    return cls


@register_method
class RemotionMethod(BaseMethod):
    NAME = "remotion_video"
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

    def run(
        self,
        *,
        prompt: str,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Any | None = None,
    ) -> Dict[str, Any]:
        """
        Generate video using Remotion templates
        
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

        # Calculate duration
        duration_sec = (duration_ms / 1000.0) if duration_ms else self.DEFAULT_DURATION_SEC
        
        # Ensure duration is within reasonable bounds
        if duration_sec < 3:
            duration_sec = 3
        elif duration_sec > 10:
            duration_sec = 10

        # Create output directories
        out_dir = workdir / "project" / project
        out_dir.mkdir(parents=True, exist_ok=True)
        video_dir = out_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_filename = f"{target_name}.mp4"
        output_path = video_dir / output_filename

        # Parse text to extract title and description
        # Simple parsing: if text contains "|", split on it; otherwise use as title
        if "|" in text:
            parts = text.split("|", 1)
            title = parts[0].strip()
            description = parts[1].strip()
        else:
            title = text.strip()
            description = ""

        # Create props for Remotion
        props = {
            "title": title,
            "description": description,
            "duration": duration_sec,
            "imagePath": self.DEFAULT_IMAGE,
            "titleStartTime": int(duration_sec * 0.5 * 1000),  # Start at 50% of duration
            "soundEffect": self.DEFAULT_SOUND_EFFECT
        }

        # Save props to JSON file for debugging
        props_path = out_dir / f"{target_name}_props.json"
        with open(props_path, 'w', encoding='utf-8') as f:
            json.dump(props, f, indent=2)

        try:
            # Find the remotion_project directory relative to workdir
            remotion_project_path = workdir.parent / "remotion_project"
            if not remotion_project_path.exists():
                # If not found, try relative to current working directory
                remotion_project_path = Path("remotion_project")
            
            # Use a temporary filename in remotion's output directory
            temp_output_filename = f"temp_{target_name}.mp4"
            temp_output_path = remotion_project_path / "output" / temp_output_filename
            # For the command, use relative path from remotion_project directory
            temp_output_path_for_cmd = Path("output") / temp_output_filename
            
            # Render video using Remotion
            cmd = [
                "npx", "remotion", "render",
                template_name,
                str(temp_output_path_for_cmd),
                "--props", json.dumps(props)
            ]
            
            print(f"🎬 Rendering {template_name} video...")
            print(f"📊 Props: {json.dumps(props, indent=2)}")
            print(f"📁 Output: {output_path}")
            
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
                    import shutil
                    shutil.move(str(temp_output_path), str(output_path))
                    print(f"✅ Video generated and moved successfully!")
                else:
                    return {
                        "ok": False,
                        "artifacts": [str(props_path)],
                        "error": f"Video file not found at {temp_output_path}"
                    }
                
                return {
                    "ok": True,
                    "artifacts": [str(output_path), str(props_path)],
                    "meta": {
                        "template": template_name,
                        "template_config": self.TEMPLATES[template_name],
                        "duration_sec": duration_sec,
                        "title": title,
                        "description": description,
                        "props": props,
                        "output_path": str(output_path),
                        "props_path": str(props_path)
                    },
                    "error": None,
                }
            else:
                error_msg = f"Remotion rendering failed: {result.stderr}"
                print(f"❌ {error_msg}")
                return {
                    "ok": False,
                    "artifacts": [str(props_path)],
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "Remotion rendering timed out (5 minutes)"
            print(f"❌ {error_msg}")
            return {
                "ok": False,
                "artifacts": [str(props_path)],
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "ok": False,
                "artifacts": [str(props_path)],
                "error": error_msg
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
