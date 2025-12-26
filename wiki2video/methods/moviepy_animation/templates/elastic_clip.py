from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from moviepy import VideoFileClip, ImageClip
from wiki2video.methods.moviepy_animation.base_template import (
    VideoTemplate,
    coerce_number,
    cover_clip,
    pick_field,
)

import cv2


def zoom_in_transform(get_frame, t, duration, zoom_factor=1.05):
    """
    动态缩放：从 1.0 缩放到 zoom_factor
    """
    frame = get_frame(t)
    h, w = frame.shape[:2]

    scale = 1.0 + (zoom_factor - 1.0) * (t / duration)

    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(frame, (new_w, new_h))

    x1 = (new_w - w) // 2
    y1 = (new_h - h) // 2
    cropped = resized[y1:y1 + h, x1:x1 + w]

    return cropped


@dataclass
class ElasticClipConfig:
    video_path: str
    duration: float
    original_length: float
    width: int
    height: int
    fps: int

class ElasticClip(VideoTemplate):
    Config = ElasticClipConfig

    @classmethod
    def build_config(cls, config: Dict[str, Any], assets: Dict[str, Any]) -> ElasticClipConfig:
        preview_duration = 5.0

        duration_ms = pick_field(config, ("duration_ms", "durationMs"), None)
        duration = (
            config.get("duration_sec")
            or config.get("duration")
            or (duration_ms / 1000.0 if duration_ms is not None else None)
            or (config.get("data") or {}).get("duration_ms", 0) / 1000.0
        )
        safe_duration = coerce_number(duration, preview_duration)

        video_or_image = assets.get("video") or assets.get("image")
        if not video_or_image:
            raise ValueError("ElasticClip requires a video or image asset")

        is_image = str(video_or_image).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))

        if is_image:
            original_length = 5.0
        else:
            real_video_seconds = assets.get("video_duration") or (assets.get("video_metadata") or {}).get("duration")
            original_length = coerce_number(
                pick_field(config, ("original_length", "originalLength"), real_video_seconds or preview_duration),
                real_video_seconds or preview_duration,
            )

        video_size = config.get("video_size", "1280x720")
        if isinstance(video_size, str) and "x" in video_size:
            w, h = video_size.split("x")
            width = int(w)
            height = int(h)
        elif isinstance(video_size, (tuple, list)) and len(video_size) == 2:
            width, height = int(video_size[0]), int(video_size[1])
        else:
            width, height = 1920, 1080

        fps = config.get("fps", 30)

        return ElasticClipConfig(
            video_path=str(video_or_image),
            duration=safe_duration,
            original_length=original_length,
            width=width,
            height=height,
            fps=fps,
        )

    @staticmethod
    def _playback_rate(target_duration: float, original_length: float, fps: int) -> float:
        total_frames = target_duration * fps
        original_frames = original_length * fps
        rate = original_frames / total_frames if total_frames else 1.0

        if target_duration < 5:
            return min(rate, 2.0)
        if target_duration <= 8:
            return max(rate, 0.6)
        return max(rate, 0.3)

    def render(self):
        target_size = self.size()
        zoom_factor = 1.05

        is_image = self.config.video_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))

        # -------------------------
        # 图片模式
        # -------------------------
        if is_image:
            clip = ImageClip(self.config.video_path).with_duration(self.config.duration)

            clip = clip.transform(
                lambda get_frame, t: zoom_in_transform(
                    get_frame, t, self.config.duration, zoom_factor
                )
            )

            clip = cover_clip(clip, target_size)
            return clip

        # -------------------------
        # 视频模式（无音频，最稳）
        # -------------------------
        playback_rate = self._playback_rate(
            self.config.duration,
            self.config.original_length,
            self.fps(),
        )

        clip = VideoFileClip(self.config.video_path)

        clip = clip.without_audio()

        clip = clip.with_speed_scaled(factor=playback_rate)

        clip = cover_clip(clip, target_size)
        clip = clip.with_duration(self.config.duration)

        return clip
