from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from moviepy.video import VideoClip

from wiki2video.methods.moviepy_animation.template_registry import TEMPLATE_REGISTRY


class MoviePyRenderer:
    def render(
        self,
        template_name: str,
        config_dict: Dict[str, Any],
        assets: Dict[str, Any],
        out_path: Path,
        template_config: Any | None = None,
    ) -> Path:
        if template_name not in TEMPLATE_REGISTRY:
            raise ValueError(f"Unknown template: {template_name}")

        template_cls = TEMPLATE_REGISTRY[template_name]
        config = template_config or template_cls.build_config(config_dict, assets)
        template = template_cls(config, assets)

        clip: VideoClip = template.render()
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            clip.write_videofile(
                str(out_path),
                fps=template.fps(),
                codec="libx264",
                audio_codec="aac",
                threads=4,
                preset="medium",
                logger=None,
            )
        finally:
            clip.close()
        return out_path
