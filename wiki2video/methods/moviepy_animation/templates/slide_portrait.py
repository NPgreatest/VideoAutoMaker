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
class SlidePortraitConfig:
    title: str
    description: str
    duration: float
    image_path: Optional[str]
    video_path: Optional[str]
    title_start_time: Optional[float]
    sound_effect: Optional[str]
    appear: bool
    image_mode: str
    width: int
    height: int
    fps: int


class SlidePortrait(VideoTemplate):
    Config = SlidePortraitConfig

    @classmethod
    def build_config(cls, config: Dict[str, Any], assets: Dict[str, Any]) -> SlidePortraitConfig:
        duration_ms = pick_field(config, ("duration_ms", "durationMs"), None)
        duration = (
            config.get("duration_sec")
            or config.get("duration")
            or (duration_ms / 1000.0 if duration_ms is not None else None)
            or (config.get("data") or {}).get("duration_ms", 0) / 1000.0
        )
        safe_duration = coerce_number(duration, 5.0)

        title_start_time = (
            config.get("title_start_time")
            or config.get("titleStartTime")
            or (config.get("data") or {}).get("title_start_time")
            or (config.get("data") or {}).get("titleStartTime")
        )

        video_size = config.get("video_size", "1080x1920")
        if isinstance(video_size, str) and "x" in video_size:
            w, h = video_size.split("x")
            width = int(w)
            height = int(h)
        elif isinstance(video_size, (tuple, list)) and len(video_size) == 2:
            width, height = int(video_size[0]), int(video_size[1])
        else:
            width, height = 1080, 1920

        fps = config.get("fps", 30)

        return SlidePortraitConfig(
            title=str(pick_field(config, ("title",), "")),
            description=str(pick_field(config, ("description",), "")),
            duration=safe_duration,
            image_path=str(assets.get("image")) if assets.get("image") else None,
            video_path=str(assets.get("video")) if assets.get("video") else None,
            title_start_time=coerce_number(title_start_time, None) if title_start_time is not None else None,
            sound_effect=str(pick_field(config, ("sound_effect", "soundEffect"), "")) or None,
            appear=bool(pick_field(config, ("appear",), False)),
            image_mode=str(pick_field(config, ("image_mode", "imageMode"), "top")),
            width=width,
            height=height,
            fps=fps,
        )

    # -------------------------------
    # Timing utilities
    # -------------------------------
    def _compute_timing(self) -> Dict[str, float]:
        fps = self.fps()
        total_frames = int(self.config.duration * fps)

        if self.config.title_start_time is not None:
            title_start_frame = int((self.config.title_start_time / 1000.0) * fps)
        elif self.config.title:
            title_start_frame = int(total_frames * 0.5)
        else:
            title_start_frame = int(total_frames * 0.3)

        title_end_frame = min(title_start_frame + int(total_frames * 0.1), total_frames)

        description_start_frame = title_end_frame
        description_end_frame = min(description_start_frame + int(total_frames * 0.1), total_frames)

        safe_title_start = max(0, title_start_frame)
        safe_title_end = max(safe_title_start + 1, title_end_frame)
        safe_desc_start = max(safe_title_end, description_start_frame)
        safe_desc_end = max(safe_desc_start + 1, description_end_frame)

        return {
            "title_start": safe_title_start / fps,
            "title_end": safe_title_end / fps,
            "desc_start": safe_desc_start / fps,
            "desc_end": safe_desc_end / fps,
        }

    # -------------------------------
    # Background
    # -------------------------------
    def _make_background(self):
        duration = self.config.duration
        size = self.size()
        if self.config.video_path:
            bg = VideoFileClip(self.config.video_path, audio=False)
            bg = cover_clip(bg, size)
            return bg.with_duration(duration)
        return layered_background(size, duration)

    # -------------------------------
    # Image
    # -------------------------------
    def _make_image(self, animate: bool):
        if not self.config.image_path:
            return None

        img = ImageClip(self.config.image_path)
        width, height = self.size()

        if self.config.image_mode == "cover":
            img = cover_clip(img.with_duration(self.config.duration), (width, height))
            position = (0, 0)
        else:
            target_width = width * 0.9
            target_height = height * (0.65 if self.config.image_mode == "center" else 0.5)

            scale = min(target_width / img.w, target_height / img.h)
            img = img.resized(scale).with_duration(self.config.duration)

            if self.config.image_mode == "center":
                center_y = 0.45 * height
                y_pos = center_y - img.h / 2
            else:
                y_pos = 0

            position = ("center", y_pos)

        if not animate:
            return img.with_position(position)

        fade_end = 25 / self.fps()
        spring_start = 10 / self.fps()
        spring_duration = 1.0

        def opacity(t: float) -> float:
            return progress_in_range(t, 0, fade_end)

        def scale_fn(t: float) -> float:
            progress = clamp((t - spring_start) / spring_duration)
            return 0.95 + (1 - 0.95) * ease_out_spring(progress)

        animated = img.resized(lambda t: scale_fn(t)).with_position(position)
        return self._with_opacity(animated, opacity)

    # -------------------------------
    # Title
    # -------------------------------
    def _make_title(self, animate: bool, timings: Dict[str, float], text_y: float):
        if not self.config.title:
            return None

        width, _ = self.size()
        target_width = width * 0.8
        estimated_char_width = 0.6
        font_size = min(int(target_width / (len(self.config.title) * estimated_char_width or 1)), 120)

        clip = TextClip(
            text=self.config.title,
            font_size=font_size,
            color="white",
            text_align="center",
            method="caption",
            size=(int(width * 0.9), None),
        ).with_duration(self.config.duration)

        if not animate:
            return clip.with_position(("center", text_y))

        spring_duration = 1.0

        def opacity(t: float) -> float:
            return progress_in_range(t, timings["title_start"], timings["title_end"])

        def scale_fn(t: float) -> float:
            progress = clamp((t - timings["title_start"]) / spring_duration)
            return 0.9 + (1 - 0.9) * ease_out_spring(progress)

        animated = clip.resized(lambda t: scale_fn(t)).with_position(("center", text_y))
        return self._with_opacity(animated, opacity)

    # -------------------------------
    # Description
    # -------------------------------
    def _make_description(self, animate: bool, timings: Dict[str, float], text_y: float):
        if not self.config.description:
            return None

        width, _ = self.size()
        target_width = width * 0.8
        estimated_char_width = 0.6
        base_font = min(int(target_width / (len(self.config.title) * estimated_char_width or 1)), 120)
        font_size = int(base_font * 0.5)

        clip = TextClip(
            text=self.config.title,
            font_size=font_size,
            color="white",
            text_align="center",
            size=(int(width * 0.9), None),  # 自动换行依然有效
        ).with_duration(self.config.duration)

        if not animate:
            return clip.with_position(("center", text_y))

        def opacity(t: float) -> float:
            return progress_in_range(t, timings["desc_start"], timings["desc_end"])

        def pos(t: float):
            progress = progress_in_range(t, timings["desc_start"], timings["desc_end"])
            offset = (1 - progress) * 30
            return "center", text_y + offset

        animated = clip.with_position(pos)
        return self._with_opacity(animated, opacity)

    # -------------------------------
    # Render
    # -------------------------------
    def render(self):
        animate = not self.config.appear
        timings = self._compute_timing()
        duration = self.config.duration
        width, height = self.size()

        bg = self._make_background()
        layers = [bg]

        image_clip = self._make_image(animate)
        if image_clip:
            layers.append(image_clip)

        # Text Y logic synced with SlideLandscape
        if not self.config.image_path:
            text_y = height * 0.5
        elif self.config.image_mode == "center":
            text_y = height * 0.8
        elif self.config.image_mode == "cover":
            text_y = height * 0.5
        else:
            text_y = height * 0.65

        title_clip = self._make_title(animate, timings, text_y)
        if title_clip:
            layers.append(title_clip)
            text_y = text_y + title_clip.size[1] + 12

        description_clip = self._make_description(animate, timings, text_y)
        if description_clip:
            layers.append(description_clip)

        video = CompositeVideoClip(layers, size=self.size()).with_duration(duration)

        # Audio
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

    # -------------------------------
    # Opacity mask (MoviePy v2 compliant)
    # -------------------------------
    def _with_opacity(self, clip: ImageClip, opacity_fn) -> ImageClip:
        duration = clip.duration or self.config.duration
        mask = VideoClip(
            frame_function=lambda t: np.full((int(clip.h), int(clip.w)), float(opacity_fn(t)), dtype=np.float32),
            is_mask=True,
            duration=duration,
        )
        return clip.with_mask(mask)
