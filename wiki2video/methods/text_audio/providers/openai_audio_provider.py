from pathlib import Path
import backoff
import requests

from wiki2video.config.config_manager import config
from wiki2video.config.config_vars import (
    BACKOFF_MAX_TRIES,
    BACKOFF_MAX_TIME,
)



# -------------------------------
# TTS 主函数（OpenAI）
# -------------------------------
@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=BACKOFF_MAX_TRIES,
    max_time=BACKOFF_MAX_TIME,
    jitter=backoff.random_jitter,
)
def openai_tts(text: str, out_path: Path) -> bytes:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[openai]'"
        )

    client = OpenAI(api_key=config.get("openai", "api_key"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()

    with client.audio.speech.with_streaming_response.create(
            model=config.get("openai","tts_model"),
            voice=config.get("openai","tts_character"),
            input=text,
            instructions=config.get("openai","tts_instructions"),
            response_format="mp3",
            speed=config.get("openai","tts_speed"),
    ) as response:
        # 流式写入文件
        with open(out_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
                audio_buffer.extend(chunk)

    print(f"[OpenAI TTS] ✅ Segment audio saved to {out_path}")
    return bytes(audio_buffer)
