# text_video/api_router.py
from __future__ import annotations

from wiki2video.config.config_manager import config

# Providers
from .providers.siliconflow_video_provider import (
    sf_submit_video,
    sf_check_status,
    sf_download_video,
    sf_extract_url,
)
from .providers.openai_video_provider import (
    openai_submit_video,
    openai_check_status,
    openai_download_video,
    openai_extract_url,
)
from .providers.google_video_provider import (
    google_submit_video,
    google_check_status,
    google_download_video,
    google_extract_url,
)


def get_provider():
    """
    根据 config.json 的 text_to_video 平台选择 provider
    """
    platform = config.get("platforms", "text_to_video")

    if not platform:
        raise Exception("Missing text_to_video platform in config.json")

    platform = platform.lower().strip()

    if platform == "siliconflow":
        return {
            "name": "siliconflow",
            "submit": sf_submit_video,
            "check": sf_check_status,
            "download": sf_download_video,
            "extract_url": sf_extract_url,
        }

    if platform == "openai":
        return {
            "name": "openai",
            "submit": openai_submit_video,
            "check": openai_check_status,
            "download": openai_download_video,
            "extract_url": openai_extract_url,
        }

    if platform == "google":
        return {
            "name": "google",
            "submit": google_submit_video,
            "check": google_check_status,
            "download": google_download_video,
            "extract_url": google_extract_url,
        }

    raise Exception(f"Unsupported text_to_video platform: {platform}")
