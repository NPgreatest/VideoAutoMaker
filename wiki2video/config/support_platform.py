# ======================================================================
# Supported platforms (fixed)
# ======================================================================
from typing import Dict, Sequence

SUPPORTED_PLATFORMS: Dict[str, Sequence[str]] = {
    "llm": ["openai", "siliconflow", "google"],
    "tts": ["google", "fish_audio"],
    "text_to_video": ["openai", "runway", "kling", "siliconflow"],
    "image": ["openai", "google"],
}