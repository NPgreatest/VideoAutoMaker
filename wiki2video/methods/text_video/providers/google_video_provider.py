from __future__ import annotations

from pathlib import Path
from typing import Optional

from google import genai
from google.genai.types import GenerateVideosConfig, GenerateVideosOperation, GenerateVideosResponse

from wiki2video.config.config_manager import config

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
        print(f"operation: {operation}")

        print(f"[Google] Submitted operation: {operation.name}")
        return operation.name

    except Exception as e:
        print("[Google] Submit error:", e)
        return None

def google_check_status(operation_name: str) -> dict:
    stub = GenerateVideosOperation.model_construct(name=operation_name)
    op = client.operations.get(stub)
    print(f"[Google] , op {op}")
    if not op.done:
        return {"status": "wait"}

    if op.error:
        return {"status": "error", "error": op.error}

    return {
        "status": "success",
        "operation": op,   # ✅ 唯一权威返回
    }



def google_extract_url(op: GenerateVideosOperation) -> Optional[str]:
    """
    从 completed operation 中提取 GCS 视频路径
    """
    try:
        result: GenerateVideosResponse = op.result
        if not result or not result.generated_videos:
            return None

        return result.generated_videos[0].video.uri
    except Exception as e:
        print("[Google] Extract URL error:", e)
        return None





from google.cloud import storage
from pathlib import Path

def google_download_video(gcs_uri: str, output_path: Path):
    """
    使用 google-cloud-storage SDK 下载视频
    """
    assert gcs_uri.startswith("gs://")

    _, _, bucket_name, *blob_parts = gcs_uri.split("/")
    blob_name = "/".join(blob_parts)

    bucket_client = storage.Client(
        project=config.get("google", "project_id")  # ✅ 关键修复
    )

    bucket = bucket_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(output_path))

    print(f"[Google] Video saved → {output_path}")
