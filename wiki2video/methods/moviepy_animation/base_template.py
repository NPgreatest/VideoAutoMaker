from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
from moviepy import ColorClip, ImageClip, VideoClip


@dataclass
class TemplateMetadata:
    width: int
    height: int
    fps: int


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def progress_in_range(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0
    return clamp((t - start) / (end - start))


def ease_out_spring(progress: float) -> float:
    # Light-weight spring approximation that is stable for MoviePy callbacks
    damped = math.exp(-5 * progress)
    oscillation = math.cos(progress * 8)
    return 1 - damped * oscillation


def make_linear_gradient(size: Tuple[int, int], start_color: Tuple[int, int, int], end_color: Tuple[int, int, int]) -> ImageClip:
    width, height = size
    start_arr = np.array(start_color, dtype=np.float32)
    end_arr = np.array(end_color, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    gradient = start_arr + (end_arr - start_arr) * y  # (height, 3)
    frame = np.tile(gradient[:, None, :], (1, width, 1))
    return ImageClip(np.clip(frame, 0, 255).astype("uint8"))


def make_radial_highlight(size: Tuple[int, int], center: Tuple[float, float], radius: float, strength: float = 0.1) -> np.ndarray:
    width, height = size
    cx, cy = center
    y_indices, x_indices = np.indices((height, width))
    dist = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2)
    falloff = np.clip(1 - (dist / radius), 0, 1)
    overlay = (falloff * 255 * strength).astype("uint8")
    return overlay


def layered_background(size: Tuple[int, int], duration: float) -> VideoClip:
    base = make_linear_gradient(size, (0, 0, 0), (26, 26, 26))
    width, height = size
    highlight1 = make_radial_highlight((width, height), (width * 0.2, height * 0.8), radius=min(width, height) * 0.8)
    highlight2 = make_radial_highlight((width, height), (width * 0.8, height * 0.2), radius=min(width, height) * 0.8)

    base_array = base.get_frame(0)
    stacked = base_array.astype(np.int16)

    # Add subtle highlights to all channels
    stacked = stacked.astype(np.int16)
    for i in range(3):
        stacked[:, :, i] += highlight1
        stacked[:, :, i] += highlight2
    stacked = np.clip(stacked, 0, 255).astype("uint8")

    bg = ImageClip(stacked).with_duration(duration)
    return bg


def cover_clip(clip: VideoClip, target_size: Tuple[int, int]) -> VideoClip:
    target_w, target_h = target_size

    if clip.w == 0 or clip.h == 0:
        return clip.resized( width= target_w, height = target_h)

    scale = max(target_w / clip.w, target_h / clip.h)
    resized = clip.resized(width= clip.w * scale, height = clip.h * scale)

    cropped = resized.cropped(
        width=target_w,
        height=target_h,
        x_center=resized.w / 2,
        y_center=resized.h / 2,
    )
    return cropped


def coerce_number(value: Any, fallback: float) -> float:
    try:
        if value is None or value == "":
            return fallback
        number = float(value)
        if math.isfinite(number):
            return number
    except (TypeError, ValueError):
        pass
    return fallback


def pick_field(config: Dict[str, Any], keys: Tuple[str, ...], fallback: Any) -> Any:
    for key in keys:
        if config.get(key) is not None:
            return config[key]
        if isinstance(config.get("data"), dict) and config["data"].get(key) is not None:
            return config["data"][key]
    return fallback


def pick_env_default(config: Dict[str, Any], key: str, fallback: float) -> float:
    env = config.get("env_defaults") or config.get("defaults") or config.get("env")
    if isinstance(env, dict) and env.get(key) is not None:
        return coerce_number(env[key], fallback)
    return fallback


class VideoTemplate(ABC):
    Config: Any

    def __init__(self, config: Any, assets: Dict[str, Any]):
        self.config = config
        self.assets = assets

    @classmethod
    @abstractmethod
    def build_config(cls, config: Dict[str, Any], assets: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    def render(self) -> VideoClip:
        ...

    @classmethod
    def duration_from_config(cls, config: Dict[str, Any]) -> Optional[float]:
        return None

    def size(self) -> Tuple[int, int]:
        """从配置中获取视频尺寸"""
        if hasattr(self.config, 'width') and hasattr(self.config, 'height'):
            return (self.config.width, self.config.height)
        # 向后兼容：如果没有 width/height，尝试从 video_size 解析
        if hasattr(self.config, 'video_size') and self.config.video_size:
            if isinstance(self.config.video_size, tuple):
                return self.config.video_size
            if isinstance(self.config.video_size, str) and "x" in self.config.video_size:
                w, h = self.config.video_size.split("x")
                return (int(w), int(h))
        # 默认值（向后兼容）
        return (1920, 1080)

    def fps(self) -> int:
        """从配置中获取帧率"""
        if hasattr(self.config, 'fps'):
            return self.config.fps
        # 默认值
        return 30


def silence_clip(duration: float, size: Tuple[int, int]) -> ColorClip:
    return ColorClip(size=size, color=(0, 0, 0), duration=duration)
