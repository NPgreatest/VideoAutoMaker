# text_video/providers/openai_video_provider.py
from __future__ import annotations
from pathlib import Path

from wiki2video.config.config_manager import config
from .status_adapter import normalize_status



def openai_submit_video(prompt: str, size: str) -> str | None:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[openai]'"
        )

    client = OpenAI(api_key=config.get("openai", "api_key"))
    try:
        video = client.videos.create(
            model="sora-2",
            prompt=prompt,
            size=size,
        )
        print(f"[OpenAI] Submitted: {video.id}")
        return video.id
    except Exception as e:
        print("[OpenAI] Submit error:", e)
        return None


def openai_check_status(video_id: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[openai]'"
        )

    client = OpenAI(api_key=config.get("openai", "api_key"))
    try:
        video = client.videos.retrieve(video_id)
        raw_status = video.status
        return {
            "status": normalize_status("openai", raw_status),
            "operation": video,
        }
    except Exception as e:
        return {"status": "error", "raw": {"error": str(e)}}


def openai_extract_url(operation):
    return operation.id


def openai_download_video(video_id: str, output_path: Path):
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[openai]'"
        )

    client = OpenAI(api_key=config.get("openai", "api_key"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = client.videos.download_content(video_id, variant="video")
    content.write_to_file(str(output_path))

    print(f"[OpenAI] Video saved → {output_path}")
