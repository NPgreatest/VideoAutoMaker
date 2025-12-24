from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import moviepy.audio.fx as afx
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoClip,
    VideoFileClip,
)
from moviepy.audio.fx import AudioFadeOut

from wiki2video.methods.moviepy_animation.base_template import (
    VideoTemplate,
    clamp,
    coerce_number,
    cover_clip,
    ease_out_spring,
    layered_background,
    pick_field,
    progress_in_range,
)


@dataclass
class SlideLandscapeConfig:
    title: str
    description: str
    duration: float
    image_path: Optional[str]
    video_path: Optional[str]
    image_mode: str
    sound_effect: Optional[str]
    appear: bool
    width: int
    height: int
    fps: int


class SlideLandscape(VideoTemplate):
    Config = SlideLandscapeConfig

    @classmethod
    def build_config(cls, config: Dict[str, Any], assets: Dict[str, Any]) -> SlideLandscapeConfig:
        duration_ms = pick_field(config, ("duration_ms", "durationMs"), None)
        duration = (
            config.get("duration_sec")
            or config.get("duration")
            or (duration_ms / 1000.0 if duration_ms is not None else None)
            or (config.get("data") or {}).get("duration_ms", 0) / 1000.0
        )
        safe_duration = coerce_number(duration, 5.0)

        video_size = config.get("video_size", "1920x1080")
        if isinstance(video_size, str) and "x" in video_size:
            w, h = video_size.split("x")
            width = int(w)
            height = int(h)
        elif isinstance(video_size, (tuple, list)) and len(video_size) == 2:
            width, height = int(video_size[0]), int(video_size[1])
        else:
            width, height = 1920, 1080

        fps = config.get("fps", 30)

        return SlideLandscapeConfig(
            title=str(pick_field(config, ("title",), "")),
            description=str(pick_field(config, ("description",), "")),
            duration=safe_duration,
            image_path=str(assets.get("image")) if assets.get("image") else None,
            video_path=str(assets.get("video")) if assets.get("video") else None,
            image_mode=str(pick_field(config, ("image_mode", "imageMode"), "top")),
            sound_effect=str(pick_field(config, ("sound_effect", "soundEffect"), "")) or None,
            appear=bool(pick_field(config, ("appear",), False)),
            width=width,
            height=height,
            fps=fps,
        )

    def _make_background(self) -> VideoClip:
        duration = self.config.duration
        size = self.size()
        if self.config.video_path:
            bg = VideoFileClip(self.config.video_path, audio=False)
            bg = cover_clip(bg, size)
            return bg.with_duration(duration)
        return layered_background(size, duration)

    def _make_image(self, animate: bool, y_top: float) -> Optional[ImageClip]:
        if not self.config.image_path:
            return None

        base = ImageClip(self.config.image_path)
        width, height = self.size()

        if self.config.image_mode == "cover":
            scaled = cover_clip(base.with_duration(self.config.duration), (width, height))
            position = (0, 0)
        else:
            if self.config.title:
                target_width = width * 0.85
                target_height = height * 0.45
            else:
                target_width = width * 0.70
                target_height = height * 0.70

            scale = min(target_width / base.w, target_height / base.h)
            scaled = base.resized(new_size=scale).with_duration(self.config.duration)
            position = ("center", y_top)

        if not animate:
            return scaled.with_position(position)

        fade_end = 25 / self.fps()
        scale_start = 10 / self.fps()
        spring_duration = 1.0

        def opacity(t: float) -> float:
            return progress_in_range(t, 0, fade_end)

        def scale_fn(t: float) -> float:
            progress = clamp((t - scale_start) / spring_duration)
            return 0.96 + (1 - 0.96) * ease_out_spring(progress)

        animated = scaled.resized(lambda t: scale_fn(t)).with_position(position)
        return self._with_opacity(animated, opacity)

    def _make_title(self, animate: bool, y_top: float) -> ImageClip | None | Any:
        if not self.config.title:
            return None

        width, _ = self.size()
        target_width = width * 0.8
        estimated_char_width = 0.55
        font_size = min(int(target_width / (len(self.config.title) * estimated_char_width or 1)), 90)

        clip = TextClip(
            text=self.config.title,
            font_size=font_size,
            color="white",
            text_align="center",
            size=(int(width * 0.9), None),  # 自动换行依然有效
        ).with_duration(self.config.duration)

        if not animate:
            return clip.with_position(("center", y_top))

        fade_start = 10 / self.fps()
        fade_end = 40 / self.fps()
        scale_start = 10 / self.fps()
        spring_duration = 1.0

        def opacity(t: float) -> float:
            return progress_in_range(t, fade_start, fade_end)

        def scale_fn(t: float) -> float:
            progress = clamp((t - scale_start) / spring_duration)
            return 0.92 + (1 - 0.92) * ease_out_spring(progress)

        animated = clip.resized(lambda t: scale_fn(t)).with_position(("center", y_top))
        return self._with_opacity(animated, opacity)

    def _make_description(self, animate: bool, y_top: float) -> ImageClip | None | Any:
        if not (self.config.image_path and self.config.title and self.config.description):
            return None

        width, _ = self.size()
        target_width = width * 0.8
        estimated_char_width = 0.55
        title_font = min(int(target_width / (len(self.config.title) * estimated_char_width or 1)), 90)
        font_size = int(title_font * 0.45)

        clip = TextClip(
            text=self.config.description,
            font_size=font_size,
            color="white",
            method="caption",
            size=(int(width * 0.9), None),
        ).with_duration(self.config.duration)

        if not animate:
            return clip.with_position(("center", y_top))

        fade_start = 40 / self.fps()
        fade_end = 70 / self.fps()

        def opacity(t: float) -> float:
            return progress_in_range(t, fade_start, fade_end)

        def pos(t: float):
            progress = progress_in_range(t, fade_start, fade_end)
            offset = (1 - progress) * 30
            return "center", y_top + offset

        animated = clip.with_position(pos)
        return self._with_opacity(animated, opacity)

    def render(self):
        animate = not self.config.appear
        duration = self.config.duration
        width, height = self.size()

        bg = self._make_background()
        layers = [bg]

        y_cursor = 0.05 * height if (self.config.image_path and self.config.title and self.config.image_mode == "top") else 0.1 * height

        image_clip = self._make_image(animate, y_cursor)
        if image_clip:
            layers.append(image_clip)
            if self.config.image_mode != "cover":
                y_cursor = image_clip.size[1] + y_cursor + (0.03 * height if self.config.title else 0)
            else:
                y_cursor = height * 0.55
        elif self.config.title:
            y_cursor = height * 0.35

        title_clip = self._make_title(animate, y_cursor)
        if title_clip:
            layers.append(title_clip)
            y_cursor = y_cursor + title_clip.size[1] + 20

        description_clip = self._make_description(animate, y_cursor)
        if description_clip:
            layers.append(description_clip)

        video = CompositeVideoClip(layers, size=self.size()).with_duration(duration)

        if self.config.sound_effect and os.path.exists(self.config.sound_effect):
            start = 10 / self.fps()
            sfx = (AudioFileClip(self.config.sound_effect).with_start(start)
                   .with_effects([afx.AudioLoop(duration=duration), AudioFadeOut(duration=0.3)]))

            if video.audio:
                mixed = CompositeAudioClip([video.audio.with_duration(duration), sfx])
                video = video.with_audio(mixed)
            else:
                video = video.with_audio(sfx)

        return video

    def _with_opacity(self, clip: ImageClip, opacity_fn) -> ImageClip:
        duration = clip.duration or self.config.duration
        mask = VideoClip(
            frame_function=lambda t: np.full((int(clip.h), int(clip.w)), float(opacity_fn(t)), dtype=np.float32),
            is_mask=True,
            duration=duration,
        )
        return clip.with_mask(mask)
