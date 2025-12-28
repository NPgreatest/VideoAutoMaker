# ======================================================================
# Supported platforms (fixed)
# ======================================================================
from typing import Dict, Sequence

SUPPORTED_PLATFORMS: Dict[str, Sequence[str]] = {
    "llm": ["openai", "siliconflow", "google"],
    "tts": ["openai", "google", "fish_audio"],
    "text_to_video": ["openai", "siliconflow"],
    "text_image": ["siliconflow", "openai", "google"],
}
