"""
Ad-hoc MoviePy template smoke tests using local assets.
Each test renders a short clip to verify config parsing, overlays, animations,
and sound-effect plumbing for every template.

Run from repo root:
    python test/moviepy_animation/run_tests.py

Outputs go to test/moviepy_animation/output.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

import numpy as np
from moviepy import VideoClip
from PIL import Image

# Pillow >=10 removed ANTIALIAS; patch for moviepy 1.0.x
if not hasattr(Image, "ANTIALIAS"):  # pragma: no cover - environment guard
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]

from wiki2video.methods.moviepy_animation.renderer import MoviePyRenderer

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent.parent  # repository root
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"

SAMPLE_IMAGE = Path("wiki2video/methods/remotion_animation/example_assets/openai.webp")
SAMPLE_SOUND = Path("assets/dong_effect.wav")


def generate_sample_video(dest: Path, duration: float = 6.0, size=(1080, 1920), fps: int = 30) -> Path:
    """Generate a small gradient animation video to avoid codec/metadata issues."""
    width, height = size

    def make_frame(t: float):
        # Time-varying color gradients to ensure visual movement
        xs, ys = np.meshgrid(np.linspace(0, 1, width), np.linspace(0, 1, height))
        r = 90 + 70 * np.sin(2 * np.pi * (t / duration) + xs * np.pi)
        g = 80 + 80 * np.sin(2 * np.pi * (t / (duration * 0.8)) + ys * np.pi)
        b = 70 + 60 * np.sin(2 * np.pi * (t / (duration * 1.2)) + (xs + ys) * np.pi)
        frame = np.stack([r, g, b], axis=2)
        return np.clip(frame, 0, 255).astype("uint8")

    clip = VideoClip(make_frame, duration=duration).resized(size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        str(dest),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="medium",
        logger=None,
    )
    clip.close()
    return dest


def ensure_assets() -> Dict[str, Path]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    assets: Dict[str, Path] = {}

    sample_video_path = ASSETS_DIR / "sample.mp4"
    generate_sample_video(sample_video_path)
    assets["sample.mp4"] = sample_video_path

    image_dest = ASSETS_DIR / "image.webp"
    if not image_dest.exists():
        shutil.copy2(ROOT / SAMPLE_IMAGE, image_dest)
    assets["image.webp"] = image_dest

    if SAMPLE_SOUND.exists():
        sound_dest = ASSETS_DIR / SAMPLE_SOUND.name
        if not sound_dest.exists():
            shutil.copy2(ROOT / SAMPLE_SOUND, sound_dest)
        assets[SAMPLE_SOUND.name] = sound_dest

    return {
        "video": assets["sample.mp4"],
        "image": assets["image.webp"],
        "character_video": assets["sample.mp4"],
        "sound": assets.get(SAMPLE_SOUND.name),
    }


def render_all():
    renderer = MoviePyRenderer()
    assets = ensure_assets()

    jobs: List[Dict] = [
        {
            "name": "ElasticClip",
            "config": {
                "template": "ElasticClip",
                "duration_sec": 20,
                "original_length": 5,
            },
            "assets": {"video": assets["video"]},
        },
        {
            "name": "CharacterOverlay-Landscape",
            "config": {
                "template": "CharacterOverlay-Landscape",
                "duration_sec": 5,
                "resize_ratio": 0.18,
                "position_x": 0.05,
                "position_y": 0.75,
                "appear": True,
                "appear_from": "left",
            },
            "assets": {
                "image": assets["image"],
                "video": assets["video"],  # background video to exercise video branch
            },
        },
        {
            "name": "CharacterOverlay-Portrait",
            "config": {
                "template": "CharacterOverlay-Portrait",
                "duration_sec": 5,
                "resize_ratio": 0.22,
                "position_x": 0.08,
                "position_y": 0.65,
                "appear": True,
                "appear_from": "right",
            },
            "assets": {
                "character": assets["character_video"],  # mp4 to trigger video overlay path
                "video": assets["video"],
            },
        },
        {
            "name": "Slide-Landscape",
            "config": {
                "template": "Slide-Landscape",
                "duration_sec": 5,
                "title": "Landscape Slide",
                "description": "Testing image+title+sound animation",
                "image_mode": "top",
                "sound_effect": str(assets["sound"]) if assets.get("sound") else "",
                "appear": False,  # enable animations
            },
            "assets": {
                "image": assets["image"],
                "video": assets["video"],
            },
        },
        {
            "name": "Slide-Portrait",
            "config": {
                "template": "Slide-Portrait",
                "duration_sec": 5,
                "title": "Portrait Slide",
                "description": "Fade and spring text with center image",
                "title_start_time": 1500,
                "image_mode": "center",
                "sound_effect": str(assets["sound"]) if assets.get("sound") else "",
                "appear": False,
            },
            "assets": {
                "image": assets["image"],
                "video": assets["video"],
            },
        },
    ]

    for job in jobs:
        out_path = OUTPUT_DIR / f"{job['name'].lower().replace('-', '_')}.mp4"
        print(f"[Test] Rendering {job['name']} -> {out_path}")
        renderer.render(job["name"], job["config"], job["assets"], out_path)
        print(f"[Test] Done {job['name']}")


if __name__ == "__main__":
    render_all()
    print("All template smoke tests completed. Check output/ for rendered clips.")
