#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import List

from dacite import from_dict, Config
from pydub import AudioSegment

from wiki2video.core.path_utils import get_action_output_dir, get_output_file_path
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.methods.base import BaseMethod
from wiki2video.methods.registry import register_method
from wiki2video.methods.text_audio.api_router import tts_router
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult
from wiki2video.schema.schema_registry import get_schema


# -------------------------------
# 环境变量和 Text Audio 初始化
# -------------------------------


def _split_text_into_phrases(text: str) -> List[str]:
    """根据标点拆分成短句，用于分段生成音频"""
    # 常见的中英文分隔符：句号、逗号、问号、叹号、顿号、分号
    phrases = re.split(r"(?<=[。！？!?,，、；;])", text)
    # 去掉空白和太短的片段
    return [p.strip() for p in phrases if len(p.strip()) > 0]


@register_method
class TextAudioMethod(BaseMethod):
    NAME = "text_audio"
    OUTPUT_KIND = "audio"

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for audio generation.
        Does NOT execute heavy work - just creates and saves the block.
        """
        # Ensure project_id is set (should be set by PipelineBuilder, but ensure it here)
        if not spec.config:
            spec.config = {}
        if "project_id" not in spec.config or not spec.config["project_id"]:
            spec.config["project_id"] = "default"
        
        # Parse config using schema
        schema_class = get_schema(self.NAME)
        # Use Config to allow missing fields with default values
        config = from_dict(schema_class, spec.config, config=Config(check_types=False))
        
        # Create WorkingBlock
        working_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"
        
        working_block = WorkingBlock(
            id=working_id,
            project_id=spec.config.get("project_id", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
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
            
            # Ensure project_id is set
            if "project_id" not in config_dict or not config_dict["project_id"]:
                config_dict["project_id"] = wb.project_id or "default"
            
            schema_class = get_schema(self.NAME)
            # Use Config to allow missing fields with default values
            config = from_dict(schema_class, config_dict, config=Config(check_types=False))

            # Get text and model_id
            text = config.text
            if not text or not text.strip():
                raise Exception("Text cannot be empty")

            # Split text into phrases
            phrases = _split_text_into_phrases(text)
            if not phrases:
                phrases = [text]
            
            # Get action output directory using new path structure
            project_id = wb.project_id or config_dict.get("project_id", "default")
            block_id = wb.block_id or config_dict.get("target_name", wb.id)
            action_dir = get_action_output_dir(
                project_id=project_id,
                block_id=block_id,
                method_name=wb.method_name,
                working_block_id=wb.id
            )
            
            # Generate audio segments
            segments_meta = []
            combined_audio = AudioSegment.silent(duration=0)
            cursor_ms = 0
            
            for idx, phrase in enumerate(phrases):
                segment_path = action_dir / f"seg{idx+1}.wav"
                try:
                    segment_bytes = tts_router(phrase, segment_path)
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
                    print(f"[TextAudio] Error generating segment {idx+1}: {e}")
                    continue
            
            if len(segments_meta) == 0:
                raise Exception("Audio segments cannot be empty")

            # Merge audio segments to output file
            output_path = get_output_file_path(action_dir, block_id,"wav")
            combined_audio.export(output_path, format="wav")
            total_duration = len(combined_audio) / 1000.0  # Convert to seconds
            
            print(f"[TextAudio] ✅ Combined audio exported: {output_path}")
            
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
                prev_working_block = dao.get_by_id(prev_id)
                if prev_working_block and prev_working_block.method_name == "text_audio" and prev_working_block.status == WorkingBlockStatus.SUCCESS:
                    start_time_sec = prev_working_block.accumulated_duration_sec
                    prev_result = json.loads(prev_working_block.result_json or "{}")
                    prev_duration = prev_result.get("duration_sec",0)
                    print(f"find prev text audio {prev_id} , {prev_duration}")

            wb.accumulated_duration_sec = start_time_sec + prev_duration
            wb.result_json = json.dumps({
                "status": result.status.value,
                "output_path": result.output_path,
                "duration_sec": result.duration_sec,
                "error": result.error,
                "segments": segments_meta  # 保存 segments 信息供字幕生成使用
            })

            return result
            
        except Exception as e:
            error_msg = f"Audio generation error: {str(e)}"
            print(f"[TextAudio] ❌ {error_msg}")
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
