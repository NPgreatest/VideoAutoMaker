from pathlib import Path
import backoff
import requests

from openai import OpenAI

from wiki2video.config.config_vars import (
    BACKOFF_MAX_TRIES,
    BACKOFF_MAX_TIME,
    TEXT_AUDIO_API_KEY,
OPENAI_CHARACTER
)

client = OpenAI(api_key=TEXT_AUDIO_API_KEY)


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
def openai_tts(text: str, out_path: Path, model_id: str) -> bytes:
    """
    使用 OpenAI TTS，将文本转语音，并返回音频 bytes。
    - text: 输入文本
    - out_path: 输出 mp3 路径
    - model_id: 用作 voice（如 coral / alloy / shimmer）
    """

    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()

    with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=OPENAI_CHARACTER,
            input=text,
            instructions="Speak naturally, with normal intonation.",
            response_format="mp3",
            speed=1.4,
    ) as response:
        # 流式写入文件
        with open(out_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
                audio_buffer.extend(chunk)

    print(f"[OpenAI TTS] ✅ Segment audio saved to {out_path}")
    return bytes(audio_buffer)
