# text_audio/config_vars.py

from pathlib import Path

from wiki2video.config.config_manager import config

# 全局 TTS API KEY —— 根据 platforms.tts 自动切换
TEXT_AUDIO_API_KEY = config.get_api_key(config.get("platforms", "tts"))

# 全局 backoff 配置
BACKOFF_MAX_TRIES = int(config.get("backoff_max_tries") or 5)
BACKOFF_MAX_TIME = int(config.get("backoff_max_time") or 30)

OPENAI_CHARACTER = config.get("openai_character")

WORKING_DIR = Path(config.get("working_dir") or "project").expanduser()
WORKING_DIR.mkdir(parents=True, exist_ok=True)

TEXT_TO_IMAGE_MODEL = config.get("text_to_image_model")

GENERATE_MODE = config.get("generate_mode")

# WORKINGBLOCK_POLLING_INTERVAL = int(config.get("workingblock_polling_interval") or 5)
WORKINGBLOCK_POLLING_INTERVAL = 0
WORKINGBLOCK_POLLING_COUNT_MAX = int(config.get("workingblock_polling_count_max") or 20)
WORKINGBLOCK_ERROR_COUNT_MAX = int(config.get("workingblock_error_count_max") or 3)
