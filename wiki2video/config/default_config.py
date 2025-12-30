from typing import Dict, Any


# ======================================================================
# Default config (MUST match user's real config structure)
# ======================================================================
def _default_config() -> Dict[str, Any]:
    return {
        "openai": {
            "api_key": None,
            "tts_character": "alloy",
            "llm_model": "gpt-5-nano",
            "tts_instructions": "Speak naturally, with normal intonation.",
            "tts_model": "gpt-4o-mini-tts",
            "text_image_model": "gpt-image-1-mini",
            "default_model": "gpt-4",
            "tts_speed": 1.3,
        },
        "siliconflow": {
            "api_key": None,
            "llm_model": "deepseek-ai/DeepSeek-V3.1-Terminus",
            "text_video_model": "Wan-AI/Wan2.2-T2V-A14B",
            "text_image_model": "Qwen/Qwen-Image",
            "tts_speed": 1.3,
            "default_model": "deepseek-ai/DeepSeek-V3.1-Terminus",
        },
        "google": {
            "api_key": None,
            "project_id": None,
            "output_gcs_uri": None,
            "text_image_model": "imagen-4.0-generate-001",
            "llm_model": "gemini-2.5-flash",
            "text_image_size": "2K",
            "cx_key": None,
            "tts_language_code": "en-US",
            "tts_voice_name": None,
            "tts_gender": "NEUTRAL",
            "tts_speed": 1.3,
            "tts_audio_encoding": "MP3",
        },
        "fish_audio": {
            "api_key": None,
            "model_id": None,
            "tts_model": "fish-tts-v2.3",
            "volume": -4.0,
            "speed": 1.3,
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
        "generate_mode": "video",
        "platforms": {
            "llm": "openai",
            "text_to_video": "openai",
            "tts": "openai",
            "text_image": "openai"
        },
        "ensure_output": True,
        "working_dir": "project",
        "story_mode": "long_cine",
    }
