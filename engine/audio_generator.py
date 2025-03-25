import os
import shutil
import requests

# === TTS Server Config ===
TTS_SERVER_IP = "168.4.124.31"
TTS_PORT = 9880
TTS_URL = f"http://{TTS_SERVER_IP}:{TTS_PORT}/tts?"

# Default parameters (can be modified globally)
DEFAULT_TTS_PARAMS = {
    "text_lang": "zh",
    "cut_punc": "。，",
    "speed": "1.2",
    # Optional:
    "ref_audio_path": "output/reference.wav",
    "prompt_text": "就是跟他这个成长的外部环境有关系，和本身的素质也有关系，他是一个",
    "prompt_lang": "zh",
    "text_split_method": "cut5",
    "batch_size": 1,
    "media_type": "wav",
    "streaming_mode": "true",
}

def generate_tts_audio(data, project_path, reGen=True):
    output_name = os.path.basename(project_path)
    output_audio = os.path.join(project_path, "audio")
    os.makedirs(output_audio, exist_ok=True)

    for index, block in enumerate(data["script"]):
        script = block["text"]
        audio_filename = f"{output_name}_{index + 1}.mp3"
        audio_file_path = os.path.join(output_audio, audio_filename)

        if os.path.exists(audio_file_path) and not reGen:
            print(f"Audio exists, skipping: {audio_file_path}")
            data["script"][index]["audio"] = f"audio/{audio_filename}"
            continue

        print(f"[TTS] Generating audio for: {script}")

        # Clone the default and override with current text
        params = DEFAULT_TTS_PARAMS.copy()
        params["text"] = script

        try:
            response = requests.get(TTS_URL, params=params)
            if response.status_code == 200:
                with open(audio_file_path, "wb") as f:
                    f.write(response.content)
                data["script"][index]["audio"] = f"audio/{audio_filename}"
                print(f"✅ Saved: {audio_file_path}")
            else:
                print(f"❌ Failed for {script} - HTTP {response.status_code} {response.reason}")
        except Exception as e:
            print(f"❌ Error while requesting TTS: {e}")



"""
curl --location 'http://168.4.124.31:9880/tts?text=就是跟他这个成长的外部环境有关系，和本身的素质也有关系，他是一个&text_lang=zh&ref_audio_path=output%2Freference.wav&prompt_lang=zh&prompt_text=哈喽大家好 我是NP 123的克隆人老高&text_split_method=cut5&batch_size=1&media_type=wav&streaming_mode=true'

"""