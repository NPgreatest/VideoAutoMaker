"""
text_image integration demo.

Uses the real SiliconFlow provider to generate three example images with
predefined prompts and saves them under test/text_image/output/.

Run from repo root:
    python test/text_image/test_text_image_method.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import types

# ---------------------------------------------------------------------------
# Lightweight stubs for optional heavy dependencies (keep imports working)
# ---------------------------------------------------------------------------
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    openai_stub.OpenAI = _DummyOpenAI
    sys.modules["openai"] = openai_stub

if "moviepy" not in sys.modules:
    moviepy_stub = types.ModuleType("moviepy")

    class _DummyClip:
        def __init__(self, *args, **kwargs):
            pass

        def write_videofile(self, *args, **kwargs):
            return None

        def close(self):
            return None

        def resized(self, *args, **kwargs):
            return self

        def with_duration(self, *args, **kwargs):
            return self

        def with_position(self, *args, **kwargs):
            return self

        def with_audio(self, *args, **kwargs):
            return self

        def with_start(self, *args, **kwargs):
            return self

        def with_effects(self, *args, **kwargs):
            return self

        def with_mask(self, *args, **kwargs):
            return self

        def __getattr__(self, name):
            def method(*args, **kwargs):
                return self

            return method

    class _DummyVideoClip(_DummyClip):
        pass

    def _audio_fade_out(clip, *args, **kwargs):
        return clip

    def _audio_loop(*args, **kwargs):
        return _DummyClip()

    moviepy_stub.ColorClip = _DummyClip
    moviepy_stub.ImageClip = _DummyClip
    moviepy_stub.VideoClip = _DummyVideoClip
    moviepy_stub.VideoFileClip = _DummyClip
    moviepy_stub.CompositeVideoClip = _DummyClip
    moviepy_stub.TextClip = _DummyClip
    moviepy_stub.AudioFileClip = _DummyClip
    moviepy_stub.CompositeAudioClip = _DummyClip
    moviepy_stub.vfx = types.SimpleNamespace()

    moviepy_video_stub = types.ModuleType("moviepy.video")
    moviepy_video_stub.VideoClip = _DummyVideoClip

    moviepy_audio_stub = types.ModuleType("moviepy.audio")
    moviepy_audio_fx_stub = types.ModuleType("moviepy.audio.fx")
    moviepy_audio_fx_stub.AudioFadeOut = _audio_fade_out
    moviepy_audio_fx_stub.AudioLoop = _audio_loop

    sys.modules["moviepy"] = moviepy_stub
    sys.modules["moviepy.video"] = moviepy_video_stub
    sys.modules["moviepy.audio"] = moviepy_audio_stub
    sys.modules["moviepy.audio.fx"] = moviepy_audio_fx_stub

    moviepy_stub.video = moviepy_video_stub
    moviepy_stub.audio = moviepy_audio_stub

# ---------------------------------------------------------------------------
# Local imports (after stubs)
# ---------------------------------------------------------------------------
from wiki2video.config.config_manager import config
from wiki2video.core.working_block import WorkingBlockStatus
from wiki2video.methods.text_image.method import TextImageMethod
from wiki2video.methods.text_image.schema import TextImageConfig
from wiki2video.schema.action_spec import ActionSpec


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

JOBS: List[Dict[str, str]] = [
    {
        "name": "derinkuyu_overlook",
        "prompt": (
            "Hyper-detailed aerial view of the Derinkuyu underground city entrance, "
            "sunlight pouring in, warm orange torch glow inside."
        ),
        "negative_prompt": "blurry, distorted, text overlay",
        "size": "1024x1024",
    },
    {
        "name": "subterranean_bazaar",
        "prompt": (
            "A bustling subterranean bazaar carved into volcanic rock, "
            "soft lantern lighting, traders selling spices and textiles."
        ),
        "negative_prompt": "photograph, modern clothing, washed out",
        "size": "896x1152",
    },
    {
        "name": "crystal_aquifer",
        "prompt": (
            "Fantasy illustration of an underground aquifer with glowing crystals "
            "reflecting on the water, subtle mist, explorers on a stone bridge."
        ),
        "negative_prompt": "low resolution, abstract shapes",
        "size": "1344x768",
    },
]


def _print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _require_api_key():
    key = config.get_api_key("siliconflow") or config.get("api_keys", "siliconflow_api_key")
    if not key:
        raise RuntimeError(
            "SiliconFlow API key missing. Please set api_keys.siliconflow_api_key in config.json."
        )
    return key


def _verify_result(image_path: Path):
    if not image_path.exists():
        raise AssertionError(f"Image output missing: {image_path}")
    if image_path.stat().st_size <= 0:
        raise AssertionError(f"Image output empty: {image_path}")
    print(f"[Verify] OK → {image_path} ({image_path.stat().st_size} bytes)")


def run_all_jobs():
    _print_header("Generating real SiliconFlow images")
    _ensure_output_dir()
    _require_api_key()

    method = TextImageMethod()

    for job in JOBS:
        job_dir = OUTPUT_DIR / job["name"]
        job_dir.mkdir(parents=True, exist_ok=True)

        config_obj = TextImageConfig(
            prompt=job["prompt"],
            negative_prompt=job.get("negative_prompt"),
            size=job.get("size", "1024x1024"),
            workdir=str(job_dir),
            target_name=job["name"],
            project_id="text_image_tests",
            provider="siliconflow",
        )

        print(f"[Job] Generating '{job['name']}' → workdir={job_dir}")
        action = ActionSpec(type="text_image", config=config_obj.model_dump())
        wb = method.run(action)
        wb.project_id = config_obj.project_id or wb.project_id
        wb.block_id = config_obj.target_name or wb.block_id
        poll_result = method.poll(wb)

        if poll_result.status != WorkingBlockStatus.SUCCESS:
            raise RuntimeError(f"Generation failed for {job['name']}: {poll_result.error}")

        image_path = Path(poll_result.output_path)
        _verify_result(image_path)

    print("\n🎉 Completed. Images saved to test/text_image/output/")


if __name__ == "__main__":
    run_all_jobs()
