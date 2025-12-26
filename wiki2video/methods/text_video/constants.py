from __future__ import annotations

from wiki2video.config.config_manager import config

SILICONFLOW_SUBMIT_URL = "https://api.siliconflow.cn/v1/video/submit"
SILICONFLOW_STATUS_URL = "https://api.siliconflow.cn/v1/video/status"
TEXT_TO_VIDEO_MODEL = "Wan-AI/Wan2.2-T2V-A14B"

REQUEST_TIMEOUT = 30

BACKOFF_MAX_TRIES = int(config.get("backoff_max_tries") or 5)
BACKOFF_MAX_TIME = int(config.get("backoff_max_time") or 30)
POLL_INTERVAL_SEC = 8
MAX_POLLS_PER_TASK = 120
CSV_FILENAME = "tasks.csv"

DB_PATH = "./db/video_download.csv"

# 状态
STATUS_SUBMITTED = "Submitted"
STATUS_QUEUED = "Queued"
STATUS_PROCESSING = "Processing"
STATUS_RUNNING = "Running"
STATUS_PENDING = "Pending"
STATUS_INQUEUE = "InQueue"
STATUS_INPROGRESS = "InProgress"
STATUS_SUCCEED = "Succeed"
STATUS_FAILED = "Failed"
STATUS_ERROR = "Error"
STATUS_CANCELED = "Canceled"

# text_video/constants.py

VIDEO_STATUS_SUCCESS = "success"
VIDEO_STATUS_WAIT = "wait"
VIDEO_STATUS_ERROR = "error"


NON_TERMINAL = {
    STATUS_SUBMITTED,
    STATUS_QUEUED,
    STATUS_PROCESSING,
    STATUS_RUNNING,
    STATUS_PENDING,
    STATUS_INQUEUE,
    STATUS_INPROGRESS,
}
TERMINAL = {STATUS_SUCCEED, STATUS_FAILED, STATUS_ERROR, STATUS_CANCELED}

ERRORS = {STATUS_FAILED, STATUS_ERROR}


def get_api_token() -> str | None:
    platform = config.get("platforms", "text_to_video")
    return config.get(platform, "api_key") if platform else None


def build_headers() -> dict[str, str]:
    token = get_api_token()
    return {
        "Authorization": f"Bearer {token}" if token else "",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# Default image size - will be overridden based on project config
IMAGE_SIZE = "1280x720"

# Video format configurations
FORMATS = {
    "landscape": "1280x720",
    "tiktok": "720x1280",
}
