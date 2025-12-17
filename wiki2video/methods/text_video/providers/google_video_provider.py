from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from google import genai
from google.auth.environment_vars import GOOGLE_CLOUD_QUOTA_PROJECT
from google.genai.types import GenerateVideosConfig

from wiki2video.config.config_manager import config
from .status_adapter import normalize_status


client = genai.Client(
    vertexai=True,
    project=config.get("google", "project_id"),
)

def google_submit_video(prompt: str, size: str) -> Optional[str]:

    try:
        output_gcs_uri = config.get("google", "output_gcs_uri")
        if not output_gcs_uri:
            raise ValueError("Missing google.output_gcs_uri in config.json")

        aspect_ratio = "16:9" if size in ("1280x720", "1920x1080") else "9:16"

        operation = client.models.generate_videos(
            model="veo-3.1-generate-001",
            prompt=prompt,
            config=GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                output_gcs_uri=output_gcs_uri,
            ),
        )

        print(f"[Google] Submitted operation: {operation.name}")
        return operation.name

    except Exception as e:
        print("[Google] Submit error:", e)
        return None


def google_check_status(operation_name: str) -> dict:
    """
    查询 Veo 生成状态
    """
    try:
        operation = client.operations.get(operation_name)

        if not operation.done:
            return {
                "status": normalize_status("google", "running"),
                "raw": operation,
            }

        if operation.error:
            return {
                "status": normalize_status("google", "error"),
                "raw": operation.error,
            }

        return {
            "status": normalize_status("google", "succeeded"),
            "raw": operation,
        }

    except Exception as e:
        return {
            "status": normalize_status("google", "error"),
            "raw": {"error": str(e)},
        }



def google_extract_url(raw_operation) -> Optional[str]:
    """
    从 completed operation 中提取 GCS 视频路径
    """
    try:
        videos = raw_operation.result.generated_videos
        if not videos:
            return None
        return videos[0].video.uri  # gs://bucket/path/video.mp4
    except Exception:
        return None



import subprocess

def google_download_video(gcs_uri: str, output_path: Path):
    """
    使用 gsutil 下载视频
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["gsutil", "cp", gcs_uri, str(output_path)],
        check=True,
    )

    print(f"[Google] Video saved → {output_path}")


