from typing import Dict, Any


# ======================================================================
# Default config (MUST match user’s real config structure)
# ======================================================================
def _default_config() -> Dict[str, Any]:
    return {
        "api_keys": {
            "fish_audio_api_key": None,
            "google_api_key": None,
            "openai_api_key": None,
            "runway_api_key": None,
            "siliconflow_api_key": None,
        },

        "backoff_max_time": 300,
        "backoff_max_tries": 5,

        "global_config": {
            "font_path": "assets/microhei.ttc",
            "landscape_format_picture_bottom_margin_ratio": 0.1,
            "landscape_format_picture_width_ratio": 0.15,
            "landscape_format_picture_x_ratio": 0.02,
            "landscape_format_picture_y_ratio": 0.78,
            "llm_backoff_base": 0.6,
            "llm_timeout_seconds": 120,
            "tiktok_format_picture_bottom_margin_ratio": 0.1,
            "tiktok_format_picture_width_ratio": 0.4,
            "tiktok_format_picture_x_ratio": 0.02,
            "tiktok_format_picture_y_ratio": 0.78,
        },

        "llm_default_model": "deepseek-ai/DeepSeek-V3.1-Terminus",
        "openai_character": "alloy",
        "platforms": {
            "image": "openai",
            "llm": "siliconflow",
            "text_to_video": "siliconflow",
            "tts": "fish_audio",
        },
    }
