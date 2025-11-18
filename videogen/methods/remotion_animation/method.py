#!/usr/bin/env python3
"""
Remotion Method - Video Generation using Remotion templates
Follows the BaseMethod API for video generation
"""

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from dacite import from_dict

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.methods.remotion_animation.schema import RemotionAnimationSchema
from videogen.pipeline.utils import get_character_info
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.action_spec import ActionSpec
from videogen.schema.generation_result_schema import GenerationResult
from videogen.schema.schema_registry import get_schema
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.path_utils import get_action_output_dir, get_output_file_path


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
        },
        "OverlapCharacter": {
            "width": 1920,
            "height": 1080,
            "description": "Character overlay with slide animation from left"
        },
        "OverlapCharacterTiktok": {
            "width": 1080,
            "height": 1920,
            "description": "Character overlay with slide animation from left on Tiktok Format"
        }
    }

    DEFAULT_DURATION_SEC = 5
    DEFAULT_IMAGE = "openai.png"
    DEFAULT_SOUND_EFFECT = ""

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for Remotion video generation.
        Does NOT execute heavy work - just creates and saves the block.
        """
        # Parse config using schema
        schema_class = get_schema(self.NAME)
        config = from_dict(schema_class, spec.config)
        
        # Validate template
        template_name = config.animation_type if hasattr(config, 'animation_type') else spec.config.get("template", "FilterDesktopSlide")
        if template_name not in self.TEMPLATES:
            raise ValueError(f"Invalid template '{template_name}'. Available: {list(self.TEMPLATES.keys())}")
        
        # Create WorkingBlock
        working_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        
        working_block = WorkingBlock(
            id=working_id,
            project_name=spec.config.get("project_name", "default"),
            action_id=spec.id,
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],  # Will be set by PipelineBuilder
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
            modify_time=now
        )
        
        return working_block

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        """
        Execute Remotion video generation.
        This method requires the previous job (video generation) to be completed.
        """
        try:
            # Load config from config_json
            config_dict = json.loads(wb.config_json)
            schema_class = get_schema(self.NAME)
            config = from_dict(schema_class, config_dict)
            
            # Check if previous jobs are completed
            if wb.prev_ids:
                dao = WorkingBlockDAO()
                for prev_id in wb.prev_ids:
                    prev_wb = dao.get_working_block(prev_id)
                    if not prev_wb or prev_wb.status != WorkingBlockStatus.SUCCESS:
                        # Previous job not ready yet
                        print(f"[RemotionMethod] Previous job {prev_id} not ready yet")
                        result = GenerationResult(status=WorkingBlockStatus.PENDING, output_path=None, duration_sec=None, error=None)
                        return result
                    
                    # Get video path from previous job (use the first one found)
                    if prev_wb.output_path and Path(prev_wb.output_path).exists():
                        video_path = Path(prev_wb.output_path)
                        break
                else:
                    # No valid previous job output found
                    error_msg = f"Previous job outputs not found for {wb.prev_ids}"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error
                    })
                    return result
                
                # video_path is set in the loop above
            else:
                # Try to get video path from config
                video_path_str = config_dict.get("video_path")
                if not video_path_str:
                    error_msg = "No previous job or video_path specified"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                    wb.result_json = json.dumps({
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error
                    })
                    return result
                video_path = Path(video_path_str)
            
            if not video_path.exists():
                error_msg = f"Video file not found: {video_path}"
                wb.status = WorkingBlockStatus.ERROR
                result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
                wb.result_json = json.dumps({
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error
                })
                return result
            
            # Get template and other config
            template_name = config_dict.get("template")
            if template_name not in self.TEMPLATES:
                raise Exception(f"Template {template_name} not found")
            
            # Get image and title from config
            image_filename = config_dict.get("image_filename") or self.DEFAULT_IMAGE
            title = config_dict.get("title", "")
            description = config_dict.get("description", "")
            
            # Calculate duration
            duration_ms = config_dict.get("duration_ms")
            if duration_ms:
                duration_sec = duration_ms / 1000.0
            else:
                # Try to get from video file
                try:
                    cmd = [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(video_path)
                    ]
                    result_probe = subprocess.run(cmd, capture_output=True, text=True)
                    if result_probe.returncode == 0:
                        duration_sec = float(result_probe.stdout.strip())
                    else:
                        duration_sec = self.DEFAULT_DURATION_SEC
                except Exception:
                    duration_sec = self.DEFAULT_DURATION_SEC
            
            if duration_sec < 1:
                duration_sec = 1
            
            # Get action output directory using new path structure
            workdir = Path(config_dict.get("workdir", "."))
            project_root = workdir.resolve()
            project_name = wb.project_name or config_dict.get("project_name", "default")
            block_id = wb.block_id or config_dict.get("target_name", wb.action_id)
            action_dir = get_action_output_dir(
                project_root=project_root,
                project_name=project_name,
                block_id=block_id,
                method_name=wb.method_name,
                action_id=wb.action_id
            )
            action_dir.mkdir(parents=True, exist_ok=True)
            
            # Find remotion project directory
            method_dir = Path(__file__).parent
            remotion_project_path = method_dir / "remotion_project"
            if not remotion_project_path.exists():
                remotion_project_path = Path("remotion_project")
            
            # Create assets directory
            assets_dir = remotion_project_path / "public" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            project_dir = project_root / "project" / project_name
            copied_assets = []

            def _copy_asset_if_needed(path_str: str | None) -> str | None:
                if not path_str:
                    return None
                candidate_paths = []
                user_path = Path(path_str)
                if user_path.is_absolute():
                    candidate_paths.append(user_path)
                else:
                    candidate_paths.extend([
                        project_dir / path_str,
                        Path.cwd() / path_str,
                        user_path,
                    ])
                source = next((p for p in candidate_paths if p.exists()), None)
                if not source:
                    raise FileNotFoundError(
                        f"Asset file not found: {path_str}. Tried: "
                        + ", ".join(str(p) for p in candidate_paths)
                    )
                dest_name = source.name
                dest_path = assets_dir / dest_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(dest_path))
                copied_assets.append(dest_path)
                print(f"[RemotionMethod] ✅ Copied asset {source} → {dest_path}")
                return dest_name
            
            image_asset_name = image_filename or self.DEFAULT_IMAGE
            if image_filename and image_filename != self.DEFAULT_IMAGE:
                image_asset_name = _copy_asset_if_needed(image_filename) or image_asset_name
            
            # Copy video to assets (use action_id for unique naming)
            video_filename = f"{wb.action_id}_video.mp4"
            injected_video_path = assets_dir / video_filename
            shutil.copy2(str(video_path), str(injected_video_path))
            print(f"[RemotionMethod] ✅ Copied video to remotion assets")
            
            # Calculate duration in frames (30 fps)
            REMOTION_FPS = 30
            duration_in_frames = int(round(duration_sec * REMOTION_FPS))
            
            if template_name in ("OverlapCharacter", "OverlapCharacterTiktok"):
                character = config_dict.get("character")
                char_info = get_character_info(character) or {}
                char_image_path = char_info.get("image_path")
                character_asset = None
                if char_image_path:
                    character_asset = _copy_asset_if_needed(char_image_path)
                if not character_asset:
                    # fallback to provided image asset
                    if image_asset_name and image_asset_name != self.DEFAULT_IMAGE:
                        character_asset = image_asset_name
                    else:
                        character_asset = self.DEFAULT_IMAGE
                resize_ratio = config_dict.get("resize_ratio", 0.15)
                position_x = config_dict.get("position_x", 0.02)
                position_y = config_dict.get("position_y", 0.78)
                appear = config_dict.get("appear", True)
                props = {
                    "imagePath": character_asset,
                    "resizeRatio": resize_ratio,
                    "position": {"x": position_x, "y": position_y},
                    "appear": appear,
                    "duration": duration_sec,
                    "videoPath": video_filename
                }
            elif template_name in ("FilterDesktopSlide", "FilterTikTokSlide"):
                props = {
                    "title": title,
                    "description": description,
                    "duration": duration_sec,
                    "imagePath": image_asset_name,
                    "videoPath": video_filename,
                    "titleStartTime": int(duration_sec * 0.5 * 1000),
                    "soundEffect": self.DEFAULT_SOUND_EFFECT
                }
            else:
                raise ValueError(f"Unsupported template '{template_name}'")

            output_path = get_output_file_path(action_dir, "mp4")
            
            temp_output_filename = f"temp_{wb.action_id}.mp4"
            temp_output_path = remotion_project_path / "output" / temp_output_filename
            temp_output_path_for_cmd = Path("output") / temp_output_filename
            
            frames_range = f"0-{duration_in_frames - 1}"
            cmd = [
                "npx", "remotion", "render",
                template_name,
                str(temp_output_path_for_cmd),
                "--frames", frames_range,
                "--props", json.dumps(props)
            ]
            
            print(f"[RemotionMethod] 🎬 Rendering {template_name} video for {wb.action_id}...")
            result_cmd = subprocess.run(
                cmd,
                cwd=remotion_project_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result_cmd.returncode == 0 and temp_output_path.exists():
                # Move to final location (action directory)
                shutil.move(str(temp_output_path), str(output_path))
                print(f"[RemotionMethod] ✅ Video generated successfully: {output_path}")
                
                # Clean up injected assets
                for asset_path in copied_assets:
                    if asset_path.exists():
                        asset_path.unlink()
                if injected_video_path.exists():
                    injected_video_path.unlink()
                
                # Get actual duration
                try:
                    cmd = [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(output_path)
                    ]
                    result_probe = subprocess.run(cmd, capture_output=True, text=True)
                    actual_duration = float(result_probe.stdout.strip()) if result_probe.returncode == 0 else duration_sec
                except Exception:
                    actual_duration = duration_sec
                
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
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                    "template": template_name,
                    "props": props
                })
                
                return result
            else:
                raise Exception(f"Remotion rendering failed: {result_cmd.stderr}")
                
        except subprocess.TimeoutExpired:
            error_msg = "Remotion rendering timed out (5 minutes)"
            wb.status = WorkingBlockStatus.ERROR
            result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
            wb.result_json = json.dumps({
                "status": result.status.value,
                "output_path": result.output_path,
                "duration_sec": result.duration_sec,
                "error": result.error
            })
            return result
        except Exception as e:
            error_msg = f"Remotion generation error: {str(e)}"
            print(f"[RemotionMethod] ❌ {error_msg}")
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
