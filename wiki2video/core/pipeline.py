# !/usr/bin/env python3


import json
import os
from typing import Optional

from dacite import from_dict

from wiki2video.config.config_vars import WORKING_DIR, WORKINGBLOCK_ERROR_COUNT_MAX
from wiki2video.core.concat import concat_pipeline
from wiki2video.core.utils import read_json, set_project_status, parse_project
from wiki2video.core.worker import Worker
from wiki2video.core.working_block import WorkingBlockStatus
from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.methods.registry import create_method
from wiki2video.schema.project_schema import ProjectJSON, ProjectStatus
from wiki2video.schema.project_schema import ScriptBlock


class Pipeline:

    def __init__(self, project_id: str, global_context: Optional[str] = None, dao: WorkingBlockDAO = None):
        self.project_id = project_id
        self.global_context = global_context
        self.dao = dao or WorkingBlockDAO()

    def build(self, script_block: ScriptBlock, prev_text_audio_id: Optional[str]) -> Optional[str]:
        working_blocks = []

        block_id = script_block.id

        # ---- 预先加载所有 blocks 以提高效率 ----
        all_blocks = self.dao.get_all(self.project_id)

        # ---- 遍历 ActionSpec ----
        last_wb_id = None
        text_audio_wb_id = None

        for action_index, action in enumerate(script_block.actions):

            # normalize config
            action.config = action.config or {}
            action.config.setdefault("project_id", self.project_id)
            if self.global_context is not None and action.type in {"text_audio", "text_video"}:
                action.config.setdefault("global_context", self.global_context)
            config_json = json.dumps(action.config, sort_keys=True)

            # ---- 检查是否已存在相同 project_id 和 config_json 的 working block ----
            # ---- 优先基于 (block_id + action_index + method_name) 复用 ----
            existing_wb = None
            for wb in all_blocks:
                if wb.project_id != self.project_id:
                    continue
                if wb.block_id != block_id:
                    continue
                if wb.action_index != action_index:
                    continue
                if wb.method_name != action.type:
                    continue

                # —— 已成功且输出仍存在 → 直接复用 ——
                if wb.status == WorkingBlockStatus.SUCCESS:
                    try:
                        result = json.loads(wb.result_json or "{}")
                        output_path = result.get("output_path")
                        if output_path and os.path.exists(output_path):
                            existing_wb = wb
                            break
                        # 成功但文件丢失 → 不复用
                    except Exception:
                        pass
                    continue

                # —— pending/error → 复用记录，避免重复 insert ——
                existing_wb = wb
                break


            if existing_wb:
                # 找到重复的 working block，直接跳过
                print(f"[Pipeline] ⏭️  Skipping action {action_index} ({action.type}) - duplicate config found (wb.id: {existing_wb.id})")
                last_wb_id = existing_wb.id
                
                # 保存 text_audio id（供下一 block 用）
                if action.type == "text_audio":
                    text_audio_wb_id = existing_wb.id
                
                continue

            # ---- 生成新的 WorkingBlock ----
            method = create_method(action.type)
            wb = method.run(action)

            wb.project_id = self.project_id
            wb.block_id = block_id
            wb.method_name = action.type
            wb.action_index = action_index
            wb.config_json = config_json

            # ---- 构建 prev_ids ----
            if action_index == 0 and action.type == "text_audio":
                # ★ 第一 action 且是 text_audio → 跨 block 依赖
                if prev_text_audio_id:
                    wb.prev_ids = [prev_text_audio_id]
                else:
                    wb.prev_ids = []
            else:
                # ★ 本 block 内链式依赖
                wb.prev_ids = [last_wb_id] if last_wb_id else []
                if action.type == "moviepy_animation" and action.config.get("template", None) == "ElasticClip":
                    wb.prev_ids.append(text_audio_wb_id)

            # ---- 插 DB ----
            if self.dao.insert(wb):
                last_wb_id = wb.id
                working_blocks.append(wb)

                if action.type == "text_audio":
                    text_audio_wb_id = wb.id

        # 返回本 block 的 text_audio working_block.id
        return text_audio_wb_id


def _reset_video_error_blocks(project_id: str) -> int:
    """
    Reset all video (non text_audio) blocks that are in ERROR status back to PENDING.
    Returns the count of blocks reset.
    """
    dao = WorkingBlockDAO()
    blocks = dao.get_all(project_id)
    reset_count = 0

    for wb in blocks:
        if wb.status != WorkingBlockStatus.ERROR:
            continue

        wb.status = WorkingBlockStatus.PENDING
        wb.output_path = None
        wb.result_json = ""
        dao.update(wb)
        reset_count += 1

    return reset_count


def _build_full_dag(project: ProjectJSON) -> Pipeline:
    pipeline = Pipeline(project.project_id, global_context=project.global_context)
    prev_audio = None
    for script_block in project.script:
        print(f"[Pipeline] Build DAG for ScriptBlock {script_block.id}")
        prev_audio = pipeline.build(script_block, prev_audio)
    return pipeline
#
# def rebuild_audio_timeline(project_name: str):
#     """
#     Rebuild accumulate_duration_sec for all text_audio working blocks.
#     Ensures timeline continuity even after partial retries.
#     """
#     dao = WorkingBlockDAO()
#     blocks = dao.get_all(project_name)
#
#     audio_blocks = [wb for wb in blocks if wb.method_name == "text_audio"]
#     if not audio_blocks:
#         return
#
#     # ----------------------------
#     # FIX: numeric block_id sorting (L1, L2, L10...)
#     # ----------------------------
#     import re
#     def _extract_block_num(block_id: str):
#         """
#         Extract numeric part from L1 / B23 / etc.
#         'L10' → 10, 'L2' → 2
#         If no number exists, return large value to push it back.
#         """
#         if not block_id:
#             return 10**9
#         m = re.search(r"(\d+)$", block_id)
#         return int(m.group(1)) if m else 10**9
#
#     def _block_sort_key(wb: WorkingBlock):
#         block_id = wb.block_id or ""
#         block_num = _extract_block_num(block_id)
#         action_index = wb.action_index if wb.action_index is not None else 0
#         return (block_num, action_index)
#
#     audio_blocks.sort(key=_block_sort_key)
#
#     # ----------------------------
#     # rebuild accumulate_duration_sec
#     # ----------------------------
#     current_acc = 0.0
#     last_block_id = None
#     block_acc = 0.0
#
#     for wb in audio_blocks:
#         block_id = wb.block_id or ""
#         if block_id != last_block_id:
#             block_acc = current_acc
#             last_block_id = block_id
#
#         try:
#             result = json.loads(wb.result_json or "{}")
#             if not isinstance(result, dict):
#                 result = {}
#         except Exception:
#             result = {}
#
#         dur = result.get("duration_sec") or 0.0
#         try:
#             dur = float(dur)
#         except (TypeError, ValueError):
#             dur = 0.0
#
#         # update result json
#         result["accumulate_duration_sec"] = block_acc
#         wb.result_json = json.dumps(result)
#         wb.accumulated_duration_sec = block_acc
#         dao.update(wb)
#
#         current_acc = block_acc + max(dur, 0.0)



def run_audio_pipeline(project_id : str):

    project = parse_project(project_id)
    set_project_status(project_id, ProjectStatus.AUDIO_GENERATING)
    print("[Audio Pipeline] Status -> AUDIO_GENERATING")

    pipeline = _build_full_dag(project)
    worker = Worker(project_id)

    print("[Audio Pipeline] Running text_audio blocks…")
    jobs = worker.run_until_complete(allowed_methods={"text_audio"})
    print(f"[Audio Pipeline] Completed {jobs} jobs")

    # rebuild_audio_timeline(project.project_name)

    dao = WorkingBlockDAO()
    audio_blocks = [
        wb for wb in dao.get_all(project.project_id)
        if wb.method_name == "text_audio"
    ]

    if not audio_blocks:
        set_project_status(project_id, ProjectStatus.AUDIO_READY)
        print("[Audio Pipeline] ⚠️ No audio blocks found. Status -> AUDIO_READY")
        return

    if all(wb.status == WorkingBlockStatus.SUCCESS for wb in audio_blocks):
        set_project_status(project_id, ProjectStatus.AUDIO_READY)
        print("[Audio Pipeline] ✅ Status -> AUDIO_READY")
    else:
        set_project_status(project_id, ProjectStatus.FAILED)
        print("[Audio Pipeline] ❌ Status -> FAILED")


def run_video_pipeline(project_id : str):

    project = parse_project(project_id)
    dao = WorkingBlockDAO()

    pipeline = _build_full_dag(project)
    worker = Worker(project_id)


    error_count = 0
    if error_count < WORKINGBLOCK_ERROR_COUNT_MAX:
        reset_count = _reset_video_error_blocks(project.project_id)
        if reset_count:
            print(f"[Video Pipeline] 🔁 Reset {reset_count} error blocks to pending")

        print("[Video Pipeline] Running non-audio blocks…")
        jobs = worker.run_until_complete()
        print(f"[Video Pipeline] Completed {jobs} jobs")

        blocks = dao.get_all(project.project_id)

        # collect error counts for non-audio blocks
        error_counts = [
            wb.error_count
            for wb in blocks
            if wb.method_name != "text_audio" and wb.status == WorkingBlockStatus.ERROR
        ]

        error_count = max(error_counts) if error_counts else 0

    if error_count:
        set_project_status(project_id, ProjectStatus.FAILED)
        print("[Video Pipeline] ❌ Status -> FAILED")
        return

    try:
        concat_pipeline(project.project_id)
    except Exception as exc:
        set_project_status(project_id, ProjectStatus.FAILED)
        print(f"[Video Pipeline] ❌ Concat failed: {exc}")
        raise

    set_project_status(project_id, ProjectStatus.FINISHED)
    print("[Video Pipeline] 🎉 Status -> FINISHED")
