# text_audio/config_vars.py

from wiki2video.config.config_manager import config

# 全局 TTS API KEY —— 根据 platforms.tts 自动切换
TEXT_AUDIO_API_KEY = config.get_api_key(config.get("platforms", "tts"))

# 全局 backoff 配置
BACKOFF_MAX_TRIES = int(config.get("backoff_max_tries") or 5)
BACKOFF_MAX_TIME = int(config.get("backoff_max_time") or 30)

OPENAI_CHARACTER = config.get("openai_character")