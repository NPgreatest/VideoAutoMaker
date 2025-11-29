# !/usr/bin/env python3
"""
Final clean architecture for VideoGen pipeline.

- Pipeline 负责 DAG 建立、job 调度、依赖检查、状态写入。
- Worker 只负责执行方法（method.poll），不做调度或数据库操作。
"""

import json
import os
import time

from pathlib import Path
from typing import List, Optional, Set

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.methods.registry import create_method
from videogen.pipeline.concat import concat_pipeline
from videogen.pipeline.worker import Worker
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.project_schema import ScriptBlock
from videogen.pipeline.utils import get_project_status, read_json, set_project_status
from videogen.schema.project_schema import ProjectJSON, ProjectStatus
from dacite import from_dict


class Pipeline:
    """
    The central manager:
    - Builds working blocks from ScriptBlock
    - Selects runnable jobs
    - Updates job execution results
    """

    def __init__(self, project_name: str, global_context: Optional[str] = None, dao: WorkingBlockDAO = None):
        self.project_name = project_name
        self.global_context = global_context
        self.dao = dao or WorkingBlockDAO()

    def build(self, script_block: ScriptBlock, prev_fish_audio_id: Optional[str]) -> Optional[str]:
        working_blocks = []

        block_id = script_block.id

        # ---- 预先加载所有 blocks 以提高效率 ----
        all_blocks = self.dao.get_all(self.project_name)

        # ---- 遍历 ActionSpec ----
        last_wb_id = None
        fish_audio_wb_id = None

        for action_index, action in enumerate(script_block.actions):

            # normalize config
            action.config = action.config or {}
            action.config.setdefault("project_name", self.project_name)
            if self.global_context is not None and action.type in {"fish_audio", "text_video"}:
                action.config.setdefault("global_context", self.global_context)
            config_json = json.dumps(action.config, sort_keys=True)

            # ---- 检查是否已存在相同 project_name 和 config_json 的 working block ----
            # ---- 优先基于 (block_id + action_index + method_name) 复用 ----
            existing_wb = None
            for wb in all_blocks:
                if wb.project_name != self.project_name:
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
                
                # 保存 fish_audio id（供下一 block 用）
                if action.type == "fish_audio":
                    fish_audio_wb_id = existing_wb.id
                
                continue

            # ---- 生成新的 WorkingBlock ----
            method = create_method(action.type)
            wb = method.run(action)

            wb.project_name = self.project_name
            wb.block_id = block_id
            wb.method_name = action.type
            wb.action_index = action_index
            wb.config_json = config_json

            # ---- 构建 prev_ids ----
            if action_index == 0 and action.type == "fish_audio":
                # ★ 第一 action 且是 fish_audio → 跨 block 依赖
                if prev_fish_audio_id:
                    wb.prev_ids = [prev_fish_audio_id]
                else:
                    wb.prev_ids = []
            else:
                # ★ 本 block 内链式依赖
                wb.prev_ids = [last_wb_id] if last_wb_id else []
                if action.type == "remotion_picture" and action.config.get("template", None) == "ElasticClip":
                    wb.prev_ids.append(fish_audio_wb_id)

            # ---- 插 DB ----
            if self.dao.insert(wb):
                last_wb_id = wb.id
                working_blocks.append(wb)

                if action.type == "fish_audio":
                    fish_audio_wb_id = wb.id

        # 返回本 block 的 fish_audio working_block.id
        return fish_audio_wb_id

    # ----------------------------------------------------------------------
    # 2. Dependency checking (DAG)
    # ----------------------------------------------------------------------
    def _deps_done(self, wb: WorkingBlock) -> bool:
        """
        All prev_ids must:
        - exist
        - have SUCCESS status
        - have output_path file exist
        """
        for prev_id in wb.prev_ids:
            prev_block = self.dao.get_by_id(prev_id)
            if not prev_block:
                return False

            if prev_block.status != WorkingBlockStatus.SUCCESS:
                return False

            # check file correctness
            try:
                result = json.loads(prev_block.result_json or "{}")
            except Exception:
                return False

            output_path = result.get("output_path")
            if not output_path or not os.path.exists(output_path):
                return False

        return True

    def get_next_runnable(self, allowed_methods: Optional[Set[str]] = None) -> Optional[WorkingBlock]:
        """
        Priority-based round-robin scheduling:
        - High priority first
        - Within same priority: pick the task least recently scheduled
        """

        pending = self.dao.get_pending(self.project_name)

        # 1. 过滤 method
        if allowed_methods:
            pending = [wb for wb in pending if wb.method_name in allowed_methods]

        # 2. 过滤依赖未完成的
        runnable = [wb for wb in pending if self._deps_done(wb)]
        if not runnable:
            return None

        # 3. 设置默认 priority + last_scheduled_at
        for wb in runnable:
            if wb.priority is None:
                wb.priority = 10  # 默认优先级
            if wb.last_scheduled_at is None:
                wb.last_scheduled_at = 0  # 从未调度过则优先

        # 4. 取最高优先级的一组（值越小优先级越高）
        runnable.sort(key=lambda wb: wb.priority)
        top_priority = runnable[0].priority
        tier = [wb for wb in runnable if wb.priority == top_priority]

        # 5. 从这一组里面选 last_scheduled_at 最小的
        next_job = min(tier, key=lambda wb: wb.last_scheduled_at)

        # 6. 更新 last_scheduled_at → 放到队尾
        next_job.last_scheduled_at = time.time()
        self.dao.update(next_job)

        return next_job

    # ----------------------------------------------------------------------
    # 3. Update job results
    # ----------------------------------------------------------------------
    def update_job(self, wb: WorkingBlock, result):
        """
        result = MethodResult {
            status: SUCCESS / PENDING / ERROR
            output_path: str
            duration_sec: float
            error: str
        }
        """

        wb.status = result.status
        
        # 保留已有的 result_json 中的额外字段（如 segments）
        existing_result = {}
        if wb.result_json:
            try:
                existing_result = json.loads(wb.result_json)
            except (json.JSONDecodeError, TypeError):
                existing_result = {}
        
        # 更新基本字段
        new_result = {
            "status": result.status.value,
            "output_path": result.output_path,
            "duration_sec": result.duration_sec,
            "error": result.error
        }
        
        # 保留已有的额外字段（如 segments）
        for key in existing_result:
            if key not in new_result:
                new_result[key] = existing_result[key]
        
        wb.result_json = json.dumps(new_result)

        self.dao.update(wb)


# ----------------------------------------------------------------------
# Pipeline Runner Helpers
# ----------------------------------------------------------------------
def _coerce_input_path(input_path) -> Path:
    if isinstance(input_path, Path):
        return input_path
    return Path(input_path)


def _parse_project(input_path: Path) -> ProjectJSON:
    raw = read_json(input_path)
    project_name = raw.get("project_name")
    if not project_name:
        raise RuntimeError("Missing project_name in JSON")

    if "project_status" in raw and isinstance(raw["project_status"], str):
        try:
            raw["project_status"] = ProjectStatus(raw["project_status"])
        except ValueError:
            raw["project_status"] = ProjectStatus.CREATED

    project = from_dict(ProjectJSON, raw)
    return project


def _reset_video_error_blocks(project_name: str) -> int:
    """
    Reset all video (non fish_audio) blocks that are in ERROR status back to PENDING.
    Returns the count of blocks reset.
    """
    dao = WorkingBlockDAO()
    blocks = dao.get_all(project_name)
    reset_count = 0

    for wb in blocks:
        if wb.method_name == "fish_audio":
            continue
        if wb.status != WorkingBlockStatus.ERROR:
            continue

        wb.status = WorkingBlockStatus.PENDING
        wb.output_path = None
        wb.result_json = ""
        dao.update(wb)
        reset_count += 1

    return reset_count


def _build_full_dag(project: ProjectJSON) -> Pipeline:
    pipeline = Pipeline(project.project_name, global_context=project.global_context)
    prev_audio = None
    for script_block in project.script:
        print(f"[Pipeline] Build DAG for ScriptBlock {script_block.id}")
        prev_audio = pipeline.build(script_block, prev_audio)
    return pipeline

def rebuild_audio_timeline(project_name: str):
    """
    Rebuild accumulate_duration_sec for all fish_audio working blocks.
    Ensures timeline continuity even after partial retries.
    """
    dao = WorkingBlockDAO()
    blocks = dao.get_all(project_name)

    audio_blocks = [wb for wb in blocks if wb.method_name == "fish_audio"]
    if not audio_blocks:
        return

    # ----------------------------
    # FIX: numeric block_id sorting (L1, L2, L10...)
    # ----------------------------
    import re
    def _extract_block_num(block_id: str):
        """
        Extract numeric part from L1 / B23 / etc.
        'L10' → 10, 'L2' → 2
        If no number exists, return large value to push it back.
        """
        if not block_id:
            return 10**9
        m = re.search(r"(\d+)$", block_id)
        return int(m.group(1)) if m else 10**9

    def _block_sort_key(wb: WorkingBlock):
        block_id = wb.block_id or ""
        block_num = _extract_block_num(block_id)
        action_index = wb.action_index if wb.action_index is not None else 0
        return (block_num, action_index)

    audio_blocks.sort(key=_block_sort_key)

    # ----------------------------
    # rebuild accumulate_duration_sec
    # ----------------------------
    current_acc = 0.0
    last_block_id = None
    block_acc = 0.0

    for wb in audio_blocks:
        block_id = wb.block_id or ""
        if block_id != last_block_id:
            block_acc = current_acc
            last_block_id = block_id

        try:
            result = json.loads(wb.result_json or "{}")
            if not isinstance(result, dict):
                result = {}
        except Exception:
            result = {}

        dur = result.get("duration_sec") or 0.0
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 0.0

        # update result json
        result["accumulate_duration_sec"] = block_acc
        wb.result_json = json.dumps(result)
        wb.accumulated_duration_sec = block_acc
        dao.update(wb)

        current_acc = block_acc + max(dur, 0.0)



def run_audio_pipeline(input_path):
    """
    Stage A: execute fish_audio actions only.
    """
    path = _coerce_input_path(input_path)
    raw = read_json(path)
    project_status = get_project_status(raw)

    project = _parse_project(path)
    set_project_status(path, ProjectStatus.AUDIO_GENERATING)
    print("[Audio Pipeline] Status -> AUDIO_GENERATING")

    pipeline = _build_full_dag(project)
    worker = Worker(pipeline)

    print("[Audio Pipeline] Running fish_audio blocks…")
    jobs = worker.run_until_complete(allowed_methods={"fish_audio"})
    print(f"[Audio Pipeline] Completed {jobs} jobs")

    rebuild_audio_timeline(project.project_name)

    dao = WorkingBlockDAO()
    audio_blocks = [
        wb for wb in dao.get_all(project.project_name)
        if wb.method_name == "fish_audio"
    ]

    if not audio_blocks:
        set_project_status(path, ProjectStatus.AUDIO_READY)
        print("[Audio Pipeline] ⚠️ No audio blocks found. Status -> AUDIO_READY")
        return

    if all(wb.status == WorkingBlockStatus.SUCCESS for wb in audio_blocks):
        set_project_status(path, ProjectStatus.AUDIO_READY)
        print("[Audio Pipeline] ✅ Status -> AUDIO_READY")
    else:
        set_project_status(path, ProjectStatus.FAILED)
        print("[Audio Pipeline] ❌ Status -> FAILED")


def run_video_pipeline(input_path):
    """
    Stage B: execute non-audio actions once audio is locked.
    """
    path = _coerce_input_path(input_path)
    raw = read_json(path)
    project_status = get_project_status(raw)

    # if project_status != ProjectStatus.AUDIO_READY:
    #     raise RuntimeError("Project must be AUDIO_READY before running video pipeline.")

    project = _parse_project(path)
    set_project_status(path, ProjectStatus.VIDEO_GENERATING)
    print("[Video Pipeline] Status -> VIDEO_GENERATING")

    reset_count = _reset_video_error_blocks(project.project_name)
    if reset_count:
        print(f"[Video Pipeline] 🔁 Reset {reset_count} error blocks to pending")

    pipeline = _build_full_dag(project)
    worker = Worker(pipeline)

    allowed_methods: Set[str] = {
        action.type
        for block in project.script
        for action in block.actions
        if action.type != "fish_audio"
    }

    if not allowed_methods:
        print("[Video Pipeline] No video actions detected. Marking finished.")
        set_project_status(path, ProjectStatus.FINISHED)
        return

    print("[Video Pipeline] Running non-audio blocks…")
    jobs = worker.run_until_complete(allowed_methods=allowed_methods)
    print(f"[Video Pipeline] Completed {jobs} jobs")

    dao = WorkingBlockDAO()
    blocks = dao.get_all(project.project_name)
    errors = [
        wb for wb in blocks
        if wb.method_name != "fish_audio" and wb.status == WorkingBlockStatus.ERROR
    ]
    pending = [
        wb for wb in blocks
        if wb.method_name != "fish_audio" and wb.status == WorkingBlockStatus.PENDING
    ]

    if errors or pending:
        set_project_status(path, ProjectStatus.FAILED)
        print("[Video Pipeline] ❌ Status -> FAILED")
        return

    try:
        concat_pipeline(project.project_name)
    except Exception as exc:
        set_project_status(path, ProjectStatus.FAILED)
        print(f"[Video Pipeline] ❌ Concat failed: {exc}")
        raise

    set_project_status(path, ProjectStatus.FINISHED)
    print("[Video Pipeline] 🎉 Status -> FINISHED")


def run_pipeline(input_path):
    """
    Backwards-compatible helper that executes audio stage then video stage.
    """
    path = _coerce_input_path(input_path)
    status = get_project_status(read_json(path))

    if status in (ProjectStatus.CREATED, ProjectStatus.AUDIO_GENERATING, ProjectStatus.FAILED):
        run_audio_pipeline(path)
        status = get_project_status(read_json(path))

    if status == ProjectStatus.AUDIO_READY:
        run_video_pipeline(path)
