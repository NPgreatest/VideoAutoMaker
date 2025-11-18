#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import List
from datetime import datetime

import backoff
import requests
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest, Prosody
from pydub import AudioSegment
from dacite import from_dict, Config

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.methods.audio_fish.schema import AudioFishSchema
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.action_spec import ActionSpec
from videogen.schema.generation_result_schema import GenerationResult
from videogen.schema.schema_registry import get_schema
from videogen.pipeline.utils import get_character_info
from videogen.pipeline.path_utils import get_action_output_dir, get_output_file_path

# -------------------------------
# 环境变量和 Fish Audio 初始化
# -------------------------------
load_dotenv()
AUDIO_FISH_API_KEY = os.getenv("AUDIO_FISH_API_KEY")
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))

session = Session(AUDIO_FISH_API_KEY)


def _split_text_into_phrases(text: str) -> List[str]:
    """根据标点拆分成短句，用于分段生成音频"""
    # 常见的中英文分隔符：句号、逗号、问号、叹号、顿号、分号
    phrases = re.split(r"(?<=[。！？!?,，、；;])", text)
    # 去掉空白和太短的片段
    return [p.strip() for p in phrases if len(p.strip()) > 0]


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
def _tts_fish_request_internal(text: str, out_path: Path, model_id: str) -> bytes:
    """调用 Fish Audio TTS，返回音频字节"""
    request = TTSRequest(
        text=text,
        reference_id=model_id,
        prosody=Prosody(volume=-4.0, speed=1.2)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()
    with open(out_path, "wb") as f:
        for chunk in session.tts(request):
            f.write(chunk)
            audio_buffer.extend(chunk)
    print(f"[FishTTS] ✅ Segment audio saved to {out_path}")
    return bytes(audio_buffer)


# -------------------------------
# 主方法
# -------------------------------
@register_method
class FishAudioMethod(BaseMethod):
    NAME = "fish_audio"
    OUTPUT_KIND = "audio"

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for audio generation.
        Does NOT execute heavy work - just creates and saves the block.
        """
        # Ensure project_name is set (should be set by PipelineBuilder, but ensure it here)
        if not spec.config:
            spec.config = {}
        if "project_name" not in spec.config or not spec.config["project_name"]:
            spec.config["project_name"] = "default"
        
        # Parse config using schema
        schema_class = get_schema(self.NAME)
        # Use Config to allow missing fields with default values
        config = from_dict(schema_class, spec.config, config=Config(check_types=False))
        
        # Create WorkingBlock
        working_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        
        working_block = WorkingBlock(
            id=working_id,
            project_name=spec.config.get("project_name", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
            modify_time=now
        )
        
        return working_block

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        """
        Execute audio generation.
        This is a synchronous operation - completes in one call.
        """
        try:
            # Load config from config_json
            config_dict = json.loads(wb.config_json)
            
            # Ensure project_name is set
            if "project_name" not in config_dict or not config_dict["project_name"]:
                config_dict["project_name"] = wb.project_name or "default"
            
            schema_class = get_schema(self.NAME)
            # Use Config to allow missing fields with default values
            config = from_dict(schema_class, config_dict, config=Config(check_types=False))
            
            # Get text and model_id
            text = config.text
            if not text or not text.strip():
                raise Exception("Text cannot be empty")

            # Get model_id from character if available
            model_id = None
            character = config_dict.get("character")
            if character:
                character_info = get_character_info(character)
                if character_info and "model_id" in character_info:
                    model_id = character_info["model_id"]
                    print(f"[FishTTS] Using model_id from character '{character}': {model_id}")
            
            if not model_id:
                raise Exception("Model id cannot be empty")

            # Split text into phrases
            phrases = _split_text_into_phrases(text)
            if not phrases:
                phrases = [text]
            
            # Get action output directory using new path structure
            workdir = Path(config_dict.get("workdir", "."))
            project_root = workdir.resolve()
            project_name = wb.project_name or config_dict.get("project_name", "default")
            block_id = wb.block_id or config_dict.get("target_name", wb.id)
            action_dir = get_action_output_dir(
                project_root=project_root,
                project_name=project_name,
                block_id=block_id,
                method_name=wb.method_name,
                working_block_id=wb.id
            )
            action_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate audio segments
            segments_meta = []
            combined_audio = AudioSegment.silent(duration=0)
            cursor_ms = 0
            
            for idx, phrase in enumerate(phrases):
                segment_path = action_dir / f"seg{idx+1}.wav"
                try:
                    segment_bytes = _tts_fish_request_internal(phrase, segment_path, model_id)
                    if not segment_bytes:
                        continue
                    
                    # Load audio segment to calculate duration
                    seg_audio = AudioSegment.from_file(segment_path)
                    seg_duration = len(seg_audio)
                    combined_audio += seg_audio
                    
                    segments_meta.append({
                        "index": idx + 1,
                        "start": cursor_ms / 1000.0,
                        "end": (cursor_ms + seg_duration) / 1000.0,
                        "text": phrase
                    })
                    cursor_ms += seg_duration
                except Exception as e:
                    print(f"[FishTTS] Error generating segment {idx+1}: {e}")
                    continue
            
            if len(segments_meta) == 0:
                raise Exception("Audio segments cannot be empty")

            # Merge audio segments to output file
            output_path = get_output_file_path(action_dir, "wav")
            combined_audio.export(output_path, format="wav")
            total_duration = len(combined_audio) / 1000.0  # Convert to seconds
            
            print(f"[FishTTS] ✅ Combined audio exported: {output_path}")
            
            # Update WorkingBlock
            wb.status = WorkingBlockStatus.SUCCESS
            wb.output_path = str(output_path)
            
            result = GenerationResult(
                status=WorkingBlockStatus.SUCCESS,
                output_path=str(output_path),
                duration_sec=total_duration,
                error=None
            )

            dao = WorkingBlockDAO()
            start_time_sec = 0
            prev_duration = 0
            for prev_id in wb.prev_ids:
                prev_working_block = dao.get_working_block(prev_id)
                print(f"have prev_id, prev_working_block = {prev_working_block}")
                if prev_working_block and prev_working_block.method_name == "fish_audio" and prev_working_block.status == WorkingBlockStatus.SUCCESS:
                    start_time_sec = prev_working_block.accumulated_duration_sec
                    prev_result = json.loads(prev_working_block.result_json or "{}")
                    prev_duration = prev_result.get("duration_sec",0)
                    print(f"find prev fish audio {prev_id} , {prev_duration}")

            wb.accumulated_duration_sec = start_time_sec + prev_duration
            wb.result_json = json.dumps({
                "status": result.status.value,
                "output_path": result.output_path,
                "duration_sec": result.duration_sec,
                "error": result.error
            })

            return result
            
        except Exception as e:
            error_msg = f"Audio generation error: {str(e)}"
            print(f"[FishTTS] ❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            wb.status = WorkingBlockStatus.ERROR
            result = GenerationResult(status=WorkingBlockStatus.ERROR, output_path=None, duration_sec=None, error=error_msg)
            wb.result_json = json.dumps({
                "status": result.status.value,
                "output_path": result.output_path,
                "duration_sec": result.duration_sec,
                "error": result.error
            })
            return result
