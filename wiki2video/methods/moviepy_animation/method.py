#!/usr/bin/env python3
"""
MoviePy-based animation method replacing the old Remotion pipeline.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dacite import from_dict

from wiki2video.config.config_manager import config
from wiki2video.core.paths import get_projects_root, get_project_dir, get_project_json_path
from wiki2video.methods.base import BaseMethod
from wiki2video.methods.moviepy_animation.renderer import MoviePyRenderer
from wiki2video.methods.moviepy_animation.template_registry import TEMPLATE_REGISTRY
from wiki2video.methods.registry import register_method
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.methods.text_video.constants import FORMATS
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult
from wiki2video.schema.schema_registry import get_schema
from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.core.path_utils import get_action_output_dir, get_output_file_path


@dataclass
class AssetCopyResult:
    name: str
    path: Path
    copied: bool


@register_method
class MoviePyAnimationMethod(BaseMethod):
    NAME = "moviepy_animation"  # kept for backward compatibility
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

    def __init__(self) -> None:
        super().__init__()
        self.renderer = MoviePyRenderer()

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

    def _env_defaults(self) -> Dict[str, float]:
        keys = [
            "tiktok_format_picture_width_ratio",
            "tiktok_format_picture_x_ratio",
            "tiktok_format_picture_y_ratio",
            "tiktok_format_picture_bottom_margin_ratio",
            "landscape_format_picture_width_ratio",
            "landscape_format_picture_x_ratio",
            "landscape_format_picture_y_ratio",
            "landscape_format_picture_bottom_margin_ratio",
        ]
        return {
            key: self._coalesce_numeric(config.get("global_config", key), default=0.0) or 0.0
            for key in keys
        }

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
            result_probe = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
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
    ) -> AssetCopyResult:
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
        return AssetCopyResult(dest_name, dest_path, not existed_before)

    # ------------------------------------------
    # RUN
    # ------------------------------------------
    def run(self, spec: ActionSpec) -> WorkingBlock:
        schema_class = get_schema(self.NAME)
        config = from_dict(schema_class, spec.config or {})

        if not spec.config:
            spec.config = {}
        spec.config.setdefault("project_id", "default")

        template_name = getattr(config, "animation_type", None) or (spec.config or {}).get("template")
        template_name = self.TEMPLATE_ALIASES.get(template_name, template_name)

        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"
        working_id = str(uuid.uuid4())
        config_json = dict(spec.config or {})
        config_json["template"] = template_name

        working_block = WorkingBlock(
            id=working_id,
            project_id=config_json.get("project_id", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(config_json),
            result_json="",
            create_time=now,
        )

        return working_block

    # ------------------------------------------
    # POLL
    # ------------------------------------------
    def poll(self, wb: WorkingBlock) -> GenerationResult:
        try:
            config_dict = json.loads(wb.config_json)
            template_name = config_dict.get("template") or self.DEFAULT_TEMPLATE
            template_name = self.TEMPLATE_ALIASES.get(template_name, template_name)

            if template_name not in TEMPLATE_REGISTRY:
                raise ValueError(f"Template {template_name} not found")

            template_cls = TEMPLATE_REGISTRY[template_name]
            dao = WorkingBlockDAO()


            video_path: Optional[Path] = None
            duration_sec = self._coalesce_numeric(
                config_dict.get("duration_sec"),
                config_dict.get("duration"),
                (config_dict.get("duration_ms") / 1000.0) if config_dict.get("duration_ms") else None,
                default=None,
            )

            if wb.prev_ids:
                for prev_id in wb.prev_ids:
                    prev_wb = dao.get_by_id(prev_id)

                    if not prev_wb or prev_wb.status != WorkingBlockStatus.SUCCESS:
                        return GenerationResult(
                            status=WorkingBlockStatus.PENDING,
                            output_path=None,
                            duration_sec=None,
                            error=None,
                        )

                    if prev_wb.method_name == "text_audio" and duration_sec is None:
                        result_data = json.loads(prev_wb.result_json or "{}")
                        duration_sec = result_data.get("duration_sec")
                        continue

                    if prev_wb.output_path:
                        prev_path = Path(prev_wb.output_path)
                        if prev_path.exists():
                            video_path = prev_path
                            continue

            project_id = wb.project_id or config_dict.get("project_id", "default")
            block_id = wb.block_id or config_dict.get("target_name", wb.id)

            action_dir = get_action_output_dir(
                project_id=project_id,
                block_id=block_id,
                method_name=wb.method_name,
                working_block_id=wb.id,
            )

            assets_dir = action_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            project_dir = get_project_dir(project_id)
            copied_assets: list[Path] = []

            assets: Dict[str, Optional[str | Path]] = {"video": None, "image": None}

            image_ref = (
                config_dict.get("image_filename")
                or config_dict.get("single_picture")
                or config_dict.get("image")
            )
            if image_ref:
                image_asset = self._copy_asset(image_ref, assets_dir, project_dir)
                assets["image"] = image_asset.path
                if image_asset.copied:
                    copied_assets.append(image_asset.path)

            if video_path:
                video_asset = self._copy_asset(
                    video_path,
                    assets_dir,
                    project_dir,
                    preferred_name=f"{wb.id}_video{video_path.suffix}",
                )
                assets["video"] = video_asset.path
                if video_asset.copied:
                    copied_assets.append(video_asset.path)
            else:
                assets["video"] = None

            if duration_sec is None and video_path:
                duration_sec = self._probe_video_duration(video_path)
            if duration_sec is None:
                raise ValueError("[MoviePy] Duration not specified")

            duration_sec = max(1.0, duration_sec)

            video_duration = None
            if assets.get("video"):
                video_duration = self._probe_video_duration(Path(assets["video"]))
            assets["video_duration"] = video_duration
            assets["video_metadata"] = {"duration": video_duration} if video_duration else {}

            render_config = dict(config_dict)
            render_config["template"] = template_name
            render_config["duration_sec"] = duration_sec
            render_config.setdefault("env_defaults", self._env_defaults())

            video_size = "1280x720"
            project_cfg_path = get_project_json_path(project_id)
            if project_cfg_path.exists():
                with open(project_cfg_path) as f:
                    pj = json.load(f)
                    fmt = pj.get("size", "landscape")
                    video_size = FORMATS.get(fmt, "1280x720")
            render_config["video_size"] = video_size

            template_config = template_cls.build_config(render_config, assets)

            output_path = get_output_file_path(action_dir, block_id, "mp4")

            print(f"[MoviePy] 🎬 Rendering {template_name} for {wb.id}...")
            self.renderer.render(
                template_name,
                render_config,
                assets,
                output_path,
                template_config=template_config,
            )
            print(f"[MoviePy] ✅ Video generated successfully: {output_path}")

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
                result_probe = subprocess.run(
                    cmd_probe,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result_probe.returncode == 0:
                    actual_duration = float(result_probe.stdout.strip())
            except Exception:
                pass

            wb.status = WorkingBlockStatus.SUCCESS
            wb.output_path = str(output_path)

            max_prev_end = 0.0
            for prev_id in wb.prev_ids:
                prev_wb = dao.get_by_id(prev_id)
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
                    "template": template_name,
                    "config": asdict(template_config) if template_config else {},
                }
            )

            return result

        except subprocess.TimeoutExpired:
            error_msg = "MoviePy rendering timed out"
            wb.status = WorkingBlockStatus.ERROR
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                output_path=None,
                duration_sec=None,
                error=error_msg,
            )

        except Exception as e:
            error_msg = f"MoviePy generation error: {str(e)}"
            print(f"[MoviePy] ⚠️ {error_msg}")
            import traceback

            traceback.print_exc()

            wb.status = WorkingBlockStatus.ERROR
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                output_path=None,
                duration_sec=None,
                error=error_msg,
            )
