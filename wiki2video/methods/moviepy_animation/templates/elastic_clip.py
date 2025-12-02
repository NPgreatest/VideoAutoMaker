from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from moviepy import VideoFileClip, vfx

from wiki2video.methods.moviepy_animation.base_template import (
    TemplateMetadata,
    VideoTemplate,
    coerce_number,
    cover_clip,
    pick_field,
)


@dataclass
class ElasticClipConfig:
    video_path: str
    duration: float
    original_length: float


class ElasticClip(VideoTemplate):
    metadata = TemplateMetadata(width=1080, height=1920, fps=30)
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

        real_video_seconds = assets.get("video_duration") or (assets.get("video_metadata") or {}).get("duration")
        original_length = coerce_number(
            pick_field(config, ("original_length", "originalLength"), real_video_seconds or preview_duration),
            real_video_seconds or preview_duration,
        )

        video_path = assets.get("video")
        if not video_path:
            raise ValueError("ElasticClip requires a video asset")

        return ElasticClipConfig(
            video_path=str(video_path),
            duration=safe_duration,
            original_length=original_length,
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
        playback_rate = self._playback_rate(
            self.config.duration,
            self.config.original_length,
            self.metadata.fps,
        )

        clip = VideoFileClip(self.config.video_path)
        clip = clip.with_speed_scaled(factor=playback_rate)

        # 你的 cover 函数应仍然兼容（resize+crop）
        clip = cover_clip(clip, target_size)

        # 设置最终时长
        clip = clip.with_duration(self.config.duration)

        return clip
