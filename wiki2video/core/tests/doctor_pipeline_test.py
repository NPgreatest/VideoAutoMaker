from __future__ import annotations

import json
from pathlib import Path

from wiki2video.core.paths import get_project_dir, get_project_json_path
from wiki2video.core.pipeline import run_audio_pipeline, run_video_pipeline
from wiki2video.core.utils import write_json


def run_pipeline_smoke_test() -> None:
    """
    Run a minimal end-to-end pipeline using the built-in doctor pipeline_test.json.

    Raises:
        RuntimeError if any step fails.
    """

    # ---------------------------------------------------------
    # 1. Locate pipeline test JSON (assets)
    # ---------------------------------------------------------
    assets_dir = Path(__file__).resolve().parents[2] / "assets" / "doctor"
    test_json_path = assets_dir / "pipeline_test.json"

    if not test_json_path.exists():
        raise RuntimeError(f"pipeline_test.json not found at {test_json_path}")

    with test_json_path.open("r", encoding="utf-8") as f:
        project_json = json.load(f)

    project_id = project_json.get("project_name")
    if not project_id:
        raise RuntimeError("pipeline_test.json missing project_name")

    # ---------------------------------------------------------
    # 2. Create project dir + write project JSON
    # ---------------------------------------------------------
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    project_json_path = get_project_json_path(project_id)
    write_json(project_json_path, project_json)

    print(f"[doctor] 🧪 Pipeline smoke test project created: {project_id}")

    try:
        # ---------------------------------------------------------
        # 3. Run full pipeline
        # ---------------------------------------------------------
        run_audio_pipeline(project_id)
        run_video_pipeline(project_id)

        # ---------------------------------------------------------
        # 4. Validate output
        # ---------------------------------------------------------
        final_video = project_dir / f"{project_id}.mp4"

        if not final_video.exists():
            raise RuntimeError("Final video was not generated")

        if final_video.stat().st_size < 1024:
            raise RuntimeError("Final video exists but is too small (likely invalid)")

        print("[doctor] ✅ Pipeline smoke test passed")

    finally:
        # ---------------------------------------------------------
        # 5. Cleanup (always)
        # ---------------------------------------------------------
        print("[doctor] 🧹 ...")
