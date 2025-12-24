# text_video/providers/siliconflow_video_provider.py
from __future__ import annotations
import requests
from pathlib import Path
import backoff

from wiki2video.methods.text_video.constants import (
    SILICONFLOW_SUBMIT_URL,
    SILICONFLOW_STATUS_URL,
    TEXT_TO_VIDEO_MODEL,
    REQUEST_TIMEOUT,
    BACKOFF_MAX_TRIES,
    BACKOFF_MAX_TIME,
    build_headers,
)
from .status_adapter import normalize_status


def sf_submit_video(prompt: str, size: str) -> str | None:
    try:
        r = requests.post(
            SILICONFLOW_SUBMIT_URL,
            headers=build_headers(),
            json={"model": TEXT_TO_VIDEO_MODEL, "prompt": prompt, "image_size": size},
            timeout=REQUEST_TIMEOUT,
        )
        data = r.json()
        request_id = data.get("requestId")
        print(f"[SF] Submitted: {request_id}")
        return request_id
    except Exception as e:
        print("[SF] Submit error:", e)
        return None


@backoff.on_exception(
    backoff.expo,
    (Exception,),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME
)
def sf_check_status(request_id: str) -> dict:
    r = requests.post(
        SILICONFLOW_STATUS_URL,
        headers=build_headers(),
        json={"requestId": request_id},
        timeout=REQUEST_TIMEOUT,
    )
    raw = r.json()
    status = raw.get("status", "")
    return {
        "status": normalize_status("siliconflow", status),
        "operation": raw,  # ✅ 统一叫 operation
    }


def sf_extract_url(operation: dict) -> str | None:
    videos = operation.get("results", {}).get("videos", [])
    if videos:
        return videos[0].get("url")
    return None


def sf_download_video(url: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(1024 * 512):
                if chunk:
                    f.write(chunk)

    print(f"[SF] Video saved → {output_path}")
