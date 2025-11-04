from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

SILICONFLOW_API_TOKEN = os.getenv("SILICONFLOW_API_TOKEN")
SILICONFLOW_SUBMIT_URL = "https://api.siliconflow.cn/v1/video/submit"
SILICONFLOW_STATUS_URL = "https://api.siliconflow.cn/v1/video/status"
TEXT_TO_VIDEO_MODEL = "Wan-AI/Wan2.2-T2V-A14B"

REQUEST_TIMEOUT = 30

# Backoff retry configuration from .env
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))
POLL_INTERVAL_SEC = 8
MAX_POLLS_PER_TASK = 120
CSV_FILENAME = "tasks.csv"

DB_PATH = './db/video_download.csv'

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

NON_TERMINAL = {
    STATUS_SUBMITTED, STATUS_QUEUED, STATUS_PROCESSING, STATUS_RUNNING, STATUS_PENDING, STATUS_INQUEUE, STATUS_INPROGRESS
}
TERMINAL = {STATUS_SUCCEED, STATUS_FAILED, STATUS_ERROR, STATUS_CANCELED}

ERRORS = {STATUS_FAILED, STATUS_ERROR}

DEFAULT_HEADERS = {
    "Authorization": f"Bearer {SILICONFLOW_API_TOKEN}" if SILICONFLOW_API_TOKEN else "",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Default image size - will be overridden based on project config
IMAGE_SIZE = '1280x720'

# Video format configurations
FORMATS = {
    "landscape": "1280x720",
    "tiktok": "720x1280"
}