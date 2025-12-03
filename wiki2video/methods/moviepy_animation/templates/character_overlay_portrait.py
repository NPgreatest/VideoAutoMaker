from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
from moviepy import CompositeVideoClip, ImageClip, VideoClip, VideoFileClip

from wiki2video.methods.moviepy_animation.base_template import (
    TemplateMetadata,
    VideoTemplate,
    clamp,
    coerce_number,
    cover_clip,
    layered_background,
    pick_env_default,
    pick_field,
)


@dataclass
class CharacterOverlayPortraitConfig:
    image_path: str
    image_is_video: bool
    resize_ratio: float
    position: Dict[str, float]
    appear: bool
    appear_from: str
    duration: float
    video_path: Optional[str]


class CharacterOverlayPortrait(VideoTemplate):
    metadata = TemplateMetadata(width=1080, height=1920, fps=30)
    Config = CharacterOverlayPortraitConfig

    @classmethod
    def build_config(cls, config: Dict[str, Any], assets: Dict[str, Any]) -> CharacterOverlayPortraitConfig:
        default_image = assets.get("image") or assets.get("character")
        if not default_image:
            raise ValueError("Character overlay requires an image or character asset")

        template_name = str(config.get("template") or config.get("template_name") or "").lower()
        is_portrait = "portrait" in template_name or "tiktok" in template_name
        prefix = "TIKTOK" if is_portrait else "LANDSCAPE"

        duration_ms = pick_field(config, ("duration_ms", "durationMs"), None)
        duration = (
            config.get("duration_sec")
            or config.get("duration")
            or (duration_ms / 1000.0 if duration_ms is not None else None)
            or (config.get("data") or {}).get("duration_ms", 0) / 1000.0
        )
        safe_duration = coerce_number(duration, 5.0)

        resize_ratio = coerce_number(
            pick_field(config, ("resize_ratio",), None),
            pick_env_default(config, f"{prefix}_FORMAT_PICTURE_WIDTH_RATIO", 0.25),
        )
        position_x = coerce_number(
            pick_field(config, ("position_x",), None),
            pick_env_default(config, f"{prefix}_FORMAT_PICTURE_X_RATIO", 0.05),
        )
        position_y = coerce_number(
            pick_field(config, ("position_y",), None),
            pick_env_default(config, f"{prefix}_FORMAT_PICTURE_Y_RATIO", 0.65),
        )
        bottom_margin = coerce_number(
            pick_field(config, ("bottom_margin_ratio",), None),
            pick_env_default(config, f"{prefix}_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO", 0.0),
        )
        adjusted_y = min(position_y, max(0.0, 1 - bottom_margin)) if bottom_margin > 0 else position_y

        image_path = default_image
        image_is_video = str(image_path).lower().endswith((".mp4", ".mov", ".webm", ".mkv"))

        return CharacterOverlayPortraitConfig(
            image_path=str(image_path),
            image_is_video=image_is_video,
            resize_ratio=resize_ratio,
            position={"x": position_x, "y": adjusted_y},
            appear=bool(pick_field(config, ("appear",), True)),
            appear_from=str(pick_field(config, ("appear_from", "appearFrom"), "left")),
            duration=safe_duration,
            video_path=str(assets.get("video")) if assets.get("video") else None,
        )

    def render(self):
        duration = self.config.duration
        size = self.size()

        if self.config.video_path:
            bg = VideoFileClip(self.config.video_path, audio=False)
            bg = cover_clip(bg, size)
            bg = bg.with_duration(duration)
        else:
            bg = layered_background(size, duration)

        width, height = size
        image_width = width * self.config.resize_ratio
        image_height = image_width
        base_x = width * self.config.position["x"]
        image_y = height * self.config.position["y"]
        final_x = width - image_width - base_x if self.config.appear_from == "right" else base_x

        if self.config.image_is_video:
            # MOV with alpha support
            if str(self.config.image_path).lower().endswith(".mov"):
                overlay = VideoFileClip(self.config.image_path, has_mask=True, audio=False)
            else:
                # fallback to normal video (no alpha)
                overlay = VideoFileClip(self.config.image_path, audio=False)
        else:
            overlay = ImageClip(self.config.image_path)

        overlay = overlay.resized(new_size=(image_width, image_height)).with_duration(duration)

        animate = self.config.appear
        slide_frames = 30
        anim_duration = slide_frames / self.metadata.fps
        start_offset = image_width if self.config.appear_from == "right" else -image_width

        if animate:
            def pos(t: float):
                progress = clamp(t / anim_duration)
                offset = start_offset * (1 - progress)
                return final_x + offset, image_y

            def opacity(t: float):
                return clamp(t / anim_duration)
        else:
            def pos(t: float):
                return final_x, image_y

            def opacity(t: float):
                return 1.0

        overlay = overlay.with_position(pos)

        mask_clip = VideoClip(
            frame_function=lambda t: np.full(
                (int(image_height), int(image_width)),
                opacity(t),
                dtype=np.float32,
            ),
            is_mask=True,
        ).with_duration(duration)

        overlay = overlay.with_mask(mask_clip)

        composed = CompositeVideoClip([bg, overlay], size=size)
        composed = composed.with_duration(duration)
        return composed
