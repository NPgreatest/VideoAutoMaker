from __future__ import annotations

from typing import Dict, Type

from wiki2video.methods.moviepy_animation.base_template import VideoTemplate
from wiki2video.methods.moviepy_animation.templates import (
    ElasticClip,
    SlideLandscape,
    SlidePortrait,
)

TEMPLATE_REGISTRY: Dict[str, Type[VideoTemplate]] = {
    "ElasticClip": ElasticClip,
    "Slide-Landscape": SlideLandscape,
    "Slide-Portrait": SlidePortrait,
}
