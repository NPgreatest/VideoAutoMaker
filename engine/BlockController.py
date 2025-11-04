import os
from enum import Enum
from typing import List, Optional

from fastapi import requests

from engine.enums import RenderMode
from video_engine import generate_dalle3_image_url


class BlockController:
    def __init__(
                self,
                text: str,
                index: int,
                image_path: Optional[str],
                video_path: Optional[str],
                render_mode: RenderMode,
                audio_paths: List[str],
                genAI_prompt: str,
                prev_block: "BlockController" = None
    ):
        self.text = text
        self.index = index
        self.image_path = image_path
        self.video_path = video_path
        self.render_mode = render_mode
        self.audio_paths = audio_paths
        self.genAI_prompt = genAI_prompt
        self.prev_block = prev_block


    def genImage(self,regen_image = False):
        if self.render_mode != RenderMode.IMAGE_ONLY:
            print(f'wrong function to call in {self.render_mode} mode')
            return
        if not os.path.exists(self.image_path) or regen_image:
            print(f"🎨 Generating image for: {self.genAI_prompt}")
            image_url = generate_dalle3_image_url(self.genAI_prompt)
            if not image_url:
                print(f"❌ Failed to get image URL")
                return
            try:
                image_data = requests.get(image_url)
                image_data.raise_for_status()
                with open(self.image_path, "wb") as f:
                    f.write(image_data.content)
                # block["image"] = f"image/{image_filename}"
                print(f"📥 Image saved: {self.image_path}")
            except Exception as e:
                print(f"❌ Failed to save image: {e}")
                return
        else:
            print(f"🖼️ Using cached image: {self.image_path}")

    # def getAudio(self, regen_audio = False):
    #     script = self.text
    #     if output_name is None:
    #         output_name = os.path.basename(project_path)
    #
    #     output_audio = os.path.join(project_path, "audio")
    #     os.makedirs(output_audio, exist_ok=True)
    #
    #     character = block.get("character", "default")
    #     emotion = block.get("emotion", "愤怒")
    #
    #     # Switch speaker before processing
    #     switched = False
    #     lang = None
    #     script = block["text"]
    #     clips = split_text_into_clips(script)
    #     audio_filenames = []
    #     srt_segments = []
    #
    #     for i, clip in enumerate(clips):
    #         audio_filename = f"{output_name}_{index + 1}_{i + 1}.wav"
    #         audio_file_path = os.path.join(output_audio, audio_filename)
    #
    #         if os.path.exists(audio_file_path) and not reGen:
    #             print(f"✅ Audio exists, skipping: {audio_file_path}")
    #         else:
    #
    #             if not switched:
    #                 lang = switch_character_model(character, emotion)
    #                 switched = True
    #             print(f"[TTS] Generating audio for: {clip}")
    #             params = DEFAULT_TTS_PARAMS.copy()
    #             params["text"] = clip
    #             if lang:
    #                 params["text_lang"] = lang
    #                 params["prompt_lang"] = lang
    #             print(params)
    #             try:
    #                 response = requests.get(TTS_URL, params=params)
    #                 if response.status_code == 200:
    #                     with open(audio_file_path, "wb") as f:
    #                         f.write(response.content)
    #                     print(f"✅ Saved: {audio_file_path}")
    #                 else:
    #                     print(f"❌ Failed for {clip} - HTTP {response.status_code} {response.reason}")
    #             except Exception as e:
    #                 print(f"❌ Error requesting TTS: {e}")
    #
    #         duration = get_audio_duration(audio_file_path)
    #         start_time = current_time
    #         end_time = current_time + duration
    #         current_time = end_time
    #
    #         audio_filenames.append(f"audio/{audio_filename}")
    #         srt_segments.append(
    #             f"{len(srt_segments) + 1}\n{format_time(start_time)} --> {format_time(end_time)}\n{clip}\n\n"
    #         )
    #
    #     block["audio"] = audio_filenames
    #     return srt_segments, current_time