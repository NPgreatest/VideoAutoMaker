#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from wiki2video.core.concat import (
    run,
    ffprobe,
    normalize_clip,
    concat_videos,
    PIX_FMT,
    PRESET,
    CRF,
)
from wiki2video.core.concat import PLACEHOLDER_VIDEO, PLACEHOLDER_AUDIO


def assert_true(cond: bool, msg: str):
    if not cond:
        raise RuntimeError(f"❌ TEST FAILED: {msg}")
    print(f"✅ {msg}")


def test_placeholder_probe():
    print("\n[TEST] ffprobe placeholder files")

    assert_true(PLACEHOLDER_VIDEO.exists(), "placeholder.mp4 exists")
    assert_true(PLACEHOLDER_AUDIO.exists(), "placeholder.mp3 exists")

    vinfo = ffprobe(PLACEHOLDER_VIDEO)
    ainfo = ffprobe(PLACEHOLDER_AUDIO)

    assert_true(
        any(s["codec_type"] == "video" for s in vinfo["streams"]),
        "placeholder.mp4 has video stream",
    )
    assert_true(
        any(s["codec_type"] == "audio" for s in ainfo["streams"]),
        "placeholder.mp3 has audio stream",
    )


def test_placeholder_mux_and_concat():
    print("\n[TEST] placeholder mux → normalize → concat")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        muxed = tmp / "muxed.mp4"
        norm = tmp / "norm.mp4"
        final = tmp / "final.mp4"

        # --- mux placeholder video + audio ---
        ok = run([
            "ffmpeg", "-y",
            "-i", str(PLACEHOLDER_VIDEO),
            "-i", str(PLACEHOLDER_AUDIO),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-c:a", "aac",
            "-pix_fmt", PIX_FMT,
            "-shortest",
            str(muxed),
        ])
        assert_true(ok and muxed.exists(), "placeholder mux succeeded")

        # --- normalize ---
        ok = normalize_clip(
            src=muxed,
            dst=norm,
            w=720,
            h=1280,
            fps=30,
        )
        assert_true(ok and norm.exists(), "normalize succeeded")

        # --- concat single video ---
        ok = concat_videos([norm], final)
        assert_true(ok and final.exists(), "concat succeeded")

        # sanity check duration
        info = ffprobe(final)
        dur = float(info["format"]["duration"])
        assert_true(dur > 0.1, "final video has valid duration")



def run_concat_self_check() -> None:
    """
    Run placeholder + ffmpeg concat self-check.
    Raise RuntimeError if anything fails.
    """
    test_placeholder_probe()
    test_placeholder_mux_and_concat()


def main():
    print("🔍 Running concat / ffmpeg / placeholder self-check...")
    test_placeholder_probe()
    test_placeholder_mux_and_concat()
    print("\n🎉 ALL CONCAT TESTS PASSED")


if __name__ == "__main__":
    main()
