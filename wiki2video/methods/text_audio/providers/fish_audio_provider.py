from pathlib import Path

import backoff
import requests
from fish_audio_sdk import Session, TTSRequest, Prosody

from wiki2video.config.config_vars import TEXT_AUDIO_API_KEY, BACKOFF_MAX_TRIES, BACKOFF_MAX_TIME
from wiki2video.config.config_manager import config


# -------------------------------
# TTS 核心函数
# -------------------------------
@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter
)
def fish_tts(text: str, out_path: Path, model_id: str) -> bytes:
    """调用 Text Audio TTS，返回音频字节"""
    session = Session(TEXT_AUDIO_API_KEY)
    request = TTSRequest(
        text=text,
        reference_id=config.get("fish_audio","model_id"),
        prosody=Prosody(volume=config.get("fish_audio","volume"),
                        speed=config.get("fish_audio","speed"))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()
    with open(out_path, "wb") as f:
        for chunk in session.tts(request):
            f.write(chunk)
            audio_buffer.extend(chunk)
    print(f"[TextAudio] ✅ Segment audio saved to {out_path}")
    return bytes(audio_buffer)
