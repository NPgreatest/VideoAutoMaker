# text_audio/config_vars.py

from pathlib import Path

from wiki2video.config.config_manager import config

# 全局 TTS API KEY —— 根据 platforms.tts 自动切换
tts_platform = config.get("platforms", "tts")
TEXT_AUDIO_API_KEY = config.get(tts_platform, "api_key") if tts_platform else None

# 全局 backoff 配置
BACKOFF_MAX_TRIES = int(config.get("backoff_max_tries") or 5)
BACKOFF_MAX_TIME = int(config.get("backoff_max_time") or 30)


ENSURE_OUTPUT = config.get("ensure_output")

# WORKING_DIR is deprecated - use wiki2video.core.paths.get_projects_root() instead
# This is kept for backward compatibility but should not be used in new code
from wiki2video.core.paths import get_projects_root
WORKING_DIR = get_projects_root()

GENERATE_MODE = config.get("generate_mode")

WORKINGBLOCK_POLLING_INTERVAL = int(config.get("workingblock_polling_interval") or 2)
WORKINGBLOCK_POLLING_COUNT_MAX = int(config.get("workingblock_polling_count_max") or 20)
WORKINGBLOCK_ERROR_COUNT_MAX = int(config.get("workingblock_error_count_max") or 3)
