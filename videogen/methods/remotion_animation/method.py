#!/usr/bin/env python3
"""
Remotion Method - Video generation using pluggable Remotion templates.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dacite import from_dict

from videogen.core.config_manager import ConfigManager
from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.pipeline.utils import get_character_info
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.action_spec import ActionSpec
from videogen.schema.generation_result_schema import GenerationResult
from videogen.schema.schema_registry import get_schema
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.path_utils import get_action_output_dir, get_output_file_path


@dataclass
class TemplateDefinition:
    name: str
    entry: Path
    props_builder: Path
    width: int
    height: int
    fps: int
    dir: Path


@register_method
class RemotionMethod(BaseMethod):
    NAME = "remotion_picture"
    OUTPUT_KIND = "video"

    DEFAULT_TEMPLATE = "Slide-Landscape"
    DEFAULT_DURATION_SEC = 5
    DEFAULT_IMAGE = "openai.png"
    DEFAULT_SOUND_EFFECT = ""
    VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".mkv")

    TEMPLATE_ALIASES = {
        "Slide.Landscape": "Slide-Landscape",
        "Slide.Portrait": "Slide-Portrait",
        "CharacterOverlay.Landscape": "CharacterOverlay-Landscape",
        "CharacterOverlay.Portrait": "CharacterOverlay-Portrait",
        "FilterDesktopSlide": "Slide-Landscape",
        "FilterTikTokSlide": "Slide-Portrait",
        "OverlapCharacter": "CharacterOverlay-Landscape",
        "OverlapCharacterTiktok": "CharacterOverlay-Portrait",
    }
    def _npx_executable(self) -> str:
        default = Path(r"C:\Program Files\nodejs\npx.cmd")
        return str(default) if default.exists() else "npx"

    def __init__(self) -> None:
        super().__init__()
        self._templates_cache: Optional[Dict[str, TemplateDefinition]] = None

    @staticmethod
    def _coalesce_numeric(*values: Any, default: Optional[float] = None) -> Optional[float]:
        for value in values:
            try:
                if value is None or value == "":
                    continue
                return float(value)
            except (TypeError, ValueError):
                continue
        return default

    def _remotion_project_path(self) -> Path:
        return Path(__file__).parent / "remotion_project"

    # def _canonical_template_name(self, template_name: Optional[str]) -> str:
    #     if not template_name:
    #         return self.DEFAULT_TEMPLATE
    #     return self.TEMPLATE_ALIASES.get(template_name, template_name)

    def _discover_templates(self) -> Dict[str, TemplateDefinition]:
        if self._templates_cache is not None:
            return self._templates_cache

        templates_dir = self._remotion_project_path() / "src" / "templates"
        if not templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        templates: Dict[str, TemplateDefinition] = {}
        for template_json in templates_dir.glob("*/template.json"):
            with open(template_json, "r", encoding="utf-8") as f:
                meta = json.load(f)

            required_keys = ["name", "entry", "width", "height", "fps", "props_builder"]
            if not all(k in meta for k in required_keys):
                raise ValueError(f"Template metadata missing required keys: {template_json}")

            template_dir = template_json.parent
            name = meta["name"]
            templates[name] = TemplateDefinition(
                name=name,
                entry=(template_dir / meta["entry"]).resolve(),
                props_builder=(template_dir / meta["props_builder"]).resolve(),
                width=int(meta["width"]),
                height=int(meta["height"]),
                fps=int(meta["fps"]),
                dir=template_dir,
            )

        if not templates:
            raise ValueError(f"No templates found under {templates_dir}")

        self._templates_cache = templates
        return templates

    def _env_defaults(self) -> Dict[str, float]:
        keys = [
            "TIKTOK_FORMAT_PICTURE_WIDTH_RATIO",
            "TIKTOK_FORMAT_PICTURE_X_RATIO",
            "TIKTOK_FORMAT_PICTURE_Y_RATIO",
            "TIKTOK_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO",
            "LANDSCAPE_FORMAT_PICTURE_WIDTH_RATIO",
            "LANDSCAPE_FORMAT_PICTURE_X_RATIO",
            "LANDSCAPE_FORMAT_PICTURE_Y_RATIO",
            "LANDSCAPE_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO",
        ]
        return {key: self._coalesce_numeric(ConfigManager.get(key), default=0.0) or 0.0 for key in keys}

    def _probe_video_duration(self, video_path: Path) -> Optional[float]:
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]
            result_probe = subprocess.run(cmd, capture_output=True, text=True)
            if result_probe.returncode == 0:
                return float(result_probe.stdout.strip())
        except Exception:
            return None
        return None

    def _build_candidate_paths(self, path_str: str, project_dir: Path) -> Tuple[Path, ...]:
        user_path = Path(path_str)
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
        video_extensions = list(self.VIDEO_EXTENSIONS)

        if user_path.suffix:
            candidate_exts = [""]
            base_name = path_str
        else:
            candidate_exts = image_extensions + video_extensions
            base_name = path_str

        candidate_paths = []
        if user_path.is_absolute():
            for ext in candidate_exts:
                candidate_paths.append(user_path if not ext else Path(str(user_path) + ext))
        else:
            for ext in candidate_exts:
                full_path = base_name + ext if ext else base_name
                candidate_paths.extend(
                    [
                        project_dir / "images" / full_path,
                        project_dir / full_path,
                        project_dir / "pic" / full_path,
                        project_dir.parent.parent / "assets" / "pic" / full_path,
                        Path.cwd() / full_path,
                        Path.cwd() / "assets" / "pic" / full_path,
                        Path(full_path),
                    ]
                )
        return tuple(candidate_paths)

    def _copy_asset(
        self,
        path_like: str | Path,
        assets_dir: Path,
        project_dir: Path,
        preferred_name: Optional[str] = None,
    ) -> Tuple[str, Path, bool]:
        path_str = str(path_like)
        candidate_paths = self._build_candidate_paths(path_str, project_dir)
        source = next((p for p in candidate_paths if p.exists() and p.is_file()), None)
        if not source:
            raise FileNotFoundError(
                f"Asset file not found: {path_like}. Tried: " + ", ".join(str(p) for p in candidate_paths[:10])
            )

        dest_name = preferred_name or source.name
        dest_path = assets_dir / dest_name
        existed_before = dest_path.exists()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(dest_path))
        return dest_name, dest_path, not existed_before

    def _execute_props_builder(
        self, builder_path: Path, builder_config: Dict[str, Any], assets: Dict[str, Any], cwd: Path
    ) -> Dict[str, Any]:
        runner = Path(__file__).parent / "run_props_builder.js"

        config_json = json.dumps(builder_config, default=str)
        assets_json = json.dumps(assets, default=str)

        cmd = ["node", str(runner), str(builder_path), config_json, assets_json]
        result_cmd = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

        if result_cmd.returncode != 0:
            raise RuntimeError(
                f"Props builder failed ({builder_path}): {result_cmd.stderr or result_cmd.stdout}"
            )

        try:
            return json.loads(result_cmd.stdout or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse props_builder output: {e}\nOutput: {result_cmd.stdout}") from e

    def run(self, spec: ActionSpec) -> WorkingBlock:
        schema_class = get_schema(self.NAME)
        config = from_dict(schema_class, spec.config or {})

        template_name = getattr(config, "animation_type", None) or (spec.config or {}).get("template")
        template_name = self.TEMPLATE_ALIASES.get(template_name, template_name)


        available_templates = self._discover_templates()
        if template_name not in available_templates:
            raise ValueError(f"Invalid template '{template_name}'. Available: {list(available_templates.keys())}")

        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        working_id = str(uuid.uuid4())
        config_json = dict(spec.config or {})
        config_json["template"] = template_name

        working_block = WorkingBlock(
            id=working_id,
            project_name=config_json.get("project_name", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(config_json),
            result_json="",
            create_time=now,
            modify_time=now,
        )

        return working_block

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        try:
            config_dict = json.loads(wb.config_json)
            template_name = config_dict.get("template")
            template_name = self.TEMPLATE_ALIASES.get(template_name, template_name)
            templates = self._discover_templates()
            if template_name not in templates:
                raise ValueError(f"Template {template_name} not found")
            template = templates[template_name]

            dao = WorkingBlockDAO()

            video_path: Optional[Path] = None
            if wb.prev_ids:
                for prev_id in wb.prev_ids:
                    prev_wb = dao.get_working_block(prev_id)
                    if not prev_wb or prev_wb.status != WorkingBlockStatus.SUCCESS:
                        return GenerationResult(
                            status=WorkingBlockStatus.PENDING, output_path=None, duration_sec=None, error=None
                        )
                    if prev_wb.output_path and Path(prev_wb.output_path).exists():
                        video_path = Path(prev_wb.output_path)
                        break
                else:
                    error_msg = f"Previous job outputs not found for {wb.prev_ids}"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(
                        status=WorkingBlockStatus.ERROR,
                        output_path=None,
                        duration_sec=None,
                        error=error_msg,
                    )
                    wb.result_json = json.dumps(
                        {
                            "status": result.status.value,
                            "output_path": result.output_path,
                            "duration_sec": result.duration_sec,
                            "error": result.error,
                        }
                    )
                    return result
            else:
                video_path_str = config_dict.get("video_path")
                if not video_path_str:
                    error_msg = "No previous job or video_path specified"
                    wb.status = WorkingBlockStatus.ERROR
                    result = GenerationResult(
                        status=WorkingBlockStatus.ERROR,
                        output_path=None,
                        duration_sec=None,
                        error=error_msg,
                    )
                    wb.result_json = json.dumps(
                        {
                            "status": result.status.value,
                            "output_path": result.output_path,
                            "duration_sec": result.duration_sec,
                            "error": result.error,
                        }
                    )
                    return result
                video_path = Path(video_path_str)

            if not video_path or not video_path.exists():
                error_msg = f"Video file not found: {video_path}"
                wb.status = WorkingBlockStatus.ERROR
                result = GenerationResult(
                    status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg
                )
                wb.result_json = json.dumps(
                    {
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error,
                    }
                )
                return result

            workdir = Path(config_dict.get("workdir", ".")).resolve()
            project_name = wb.project_name or config_dict.get("project_name", "default")
            block_id = wb.block_id or config_dict.get("target_name", wb.id)
            action_dir = get_action_output_dir(
                project_root=workdir,
                project_name=project_name,
                block_id=block_id,
                method_name=wb.method_name,
                working_block_id=wb.id,
            )
            action_dir.mkdir(parents=True, exist_ok=True)

            remotion_project_path = self._remotion_project_path()
            assets_dir = remotion_project_path / "public" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            project_dir = workdir / "project" / project_name
            copied_assets: list[Path] = []

            assets: Dict[str, Optional[str]] = {"video": None, "image": None, "character": None}

            image_ref = (
                config_dict.get("image_filename")
                or config_dict.get("single_picture")
                or config_dict.get("image")
            )
            if image_ref:
                image_asset_name, image_dest, should_cleanup = self._copy_asset(
                    image_ref, assets_dir, project_dir
                )
                assets["image"] = image_asset_name
                if should_cleanup:
                    copied_assets.append(image_dest)

            character_name = config_dict.get("character")
            if character_name:
                char_info = get_character_info(character_name) or {}
                char_image_path = char_info.get("image_path")
                if char_image_path:
                    char_asset_name, char_dest, should_cleanup = self._copy_asset(
                        char_image_path, assets_dir, project_dir
                    )
                    assets["character"] = char_asset_name
                    if should_cleanup:
                        copied_assets.append(char_dest)
            if assets["character"] is None and assets["image"]:
                assets["character"] = assets["image"]

            video_dest_name, video_dest, should_cleanup = self._copy_asset(
                video_path,
                assets_dir,
                project_dir,
                preferred_name=f"{wb.id}_video{video_path.suffix or '.mp4'}",
            )
            assets["video"] = video_dest_name
            if should_cleanup:
                copied_assets.append(video_dest)

            duration_sec = self._coalesce_numeric(
                config_dict.get("duration_sec"),
                config_dict.get("duration"),
                (config_dict.get("duration_ms") / 1000.0) if config_dict.get("duration_ms") else None,
                default=None,
            )
            if duration_sec is None:
                duration_sec = self._probe_video_duration(video_path) or self.DEFAULT_DURATION_SEC
            duration_sec = max(1.0, duration_sec)

            duration_in_frames = max(1, int(round(duration_sec * template.fps)))

            builder_input = dict(config_dict)
            builder_input["template"] = template.name
            builder_input["duration_sec"] = duration_sec
            builder_input["duration_in_frames"] = duration_in_frames
            builder_input["env_defaults"] = self._env_defaults()
            props = self._execute_props_builder(template.props_builder, builder_input, assets, cwd=template.dir)

            output_path = get_output_file_path(action_dir, block_id, "mp4")
            temp_output_filename = f"temp_{wb.id}{output_path.suffix}"
            temp_output_path = remotion_project_path / "output" / temp_output_filename
            temp_output_path_for_cmd = Path("output") / temp_output_filename
            temp_output_path.parent.mkdir(parents=True, exist_ok=True)

            frames_range = f"0-{duration_in_frames - 1}"
            cmd = [
                self._npx_executable(),
                "remotion",
                "render",
                template.name,
                str(temp_output_path_for_cmd),
                "--frames",
                frames_range,
                "--props",
                json.dumps(props),
            ]

            print(f"[RemotionMethod] 🎬 Rendering {template.name} video for {wb.id}...")
            result_cmd = subprocess.run(
                cmd,
                cwd=remotion_project_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result_cmd.returncode == 0 and temp_output_path.exists():
                shutil.move(str(temp_output_path), str(output_path))
                print(f"[RemotionMethod] ✅ Video generated successfully: {output_path}")

                for asset_path in copied_assets:
                    if asset_path.exists():
                        asset_path.unlink()

                actual_duration = duration_sec
                try:
                    cmd_probe = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(output_path),
                    ]
                    result_probe = subprocess.run(cmd_probe, capture_output=True, text=True)
                    if result_probe.returncode == 0:
                        actual_duration = float(result_probe.stdout.strip())
                except Exception:
                    pass

                wb.status = WorkingBlockStatus.SUCCESS
                wb.output_path = str(output_path)

                max_prev_end = 0.0
                for prev_id in wb.prev_ids:
                    prev_wb = dao.get_working_block(prev_id)
                    if prev_wb and prev_wb.status == WorkingBlockStatus.SUCCESS:
                        prev_result = json.loads(prev_wb.result_json or "{}")
                        prev_duration = prev_result.get("duration_sec") or 0.0
                        start = prev_wb.accumulated_duration_sec or 0.0
                        max_prev_end = max(max_prev_end, start + prev_duration)
                wb.accumulated_duration_sec = max_prev_end + actual_duration

                result = GenerationResult(
                    status=WorkingBlockStatus.SUCCESS,
                    output_path=str(output_path),
                    duration_sec=actual_duration,
                    error=None,
                )
                wb.result_json = json.dumps(
                    {
                        "status": result.status.value,
                        "output_path": result.output_path,
                        "duration_sec": result.duration_sec,
                        "error": result.error,
                        "template": template.name,
                        "props": props,
                    }
                )

                return result

            raise RuntimeError(f"Remotion rendering failed: {result_cmd.stderr or result_cmd.stdout}")

        except subprocess.TimeoutExpired:
            error_msg = "Remotion rendering timed out (5 minutes)"
            wb.status = WorkingBlockStatus.ERROR
            result = GenerationResult(
                status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg
            )
            wb.result_json = json.dumps(
                {
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                }
            )
            return result
        except Exception as e:
            error_msg = f"Remotion generation error: {str(e)}"
            print(f"[RemotionMethod] ⚠️ {error_msg}")
            import traceback

            traceback.print_exc()

            wb.status = WorkingBlockStatus.ERROR
            result = GenerationResult(
                status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg
            )
            wb.result_json = json.dumps(
                {
                    "status": result.status.value,
                    "output_path": result.output_path,
                    "duration_sec": result.duration_sec,
                    "error": result.error,
                }
            )
            return result
