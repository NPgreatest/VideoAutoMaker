# !/usr/bin/env python3
"""
Final clean architecture for VideoGen pipeline.

- Pipeline 负责 DAG 建立、job 调度、依赖检查、状态写入。
- Worker 只负责执行方法（method.poll），不做调度或数据库操作。
"""

import json
import os
from typing import List, Optional

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.methods.registry import create_method
from videogen.pipeline.worker import Worker
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from videogen.schema.project_schema import ScriptBlock
from videogen.pipeline.utils import read_json, set_project_status
from videogen.schema.project_schema import ProjectJSON, ProjectStatus
from dacite import from_dict


class Pipeline:
    """
    The central manager:
    - Builds working blocks from ScriptBlock
    - Selects runnable jobs
    - Updates job execution results
    """

    def __init__(self, project_name: str, dao: WorkingBlockDAO = None):
        self.project_name = project_name
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
            config_json = json.dumps(action.config, sort_keys=True)

            # ---- 检查是否已存在相同 project_name 和 config_json 的 working block ----
            existing_wb = None
            for wb in all_blocks:
                if (wb.project_name == self.project_name and 
                    wb.config_json == config_json and
                    wb.status == WorkingBlockStatus.SUCCESS):
                    # 检查输出文件是否存在
                    try:
                        result = json.loads(wb.result_json or "{}")
                        output_path = result.get("output_path")
                        if output_path and os.path.exists(output_path):
                            existing_wb = wb
                            break
                    except Exception:
                        continue

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
            prev_block = self.dao.get_working_block(prev_id)
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

    def get_next_runnable(self) -> Optional[WorkingBlock]:
        """Return a PENDING block whose dependencies are all satisfied."""
        for wb in self.dao.get_pending(self.project_name):
            if self._deps_done(wb):
                return wb
        return None

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
        wb.result_json = json.dumps({
            "status": result.status.value,
            "output_path": result.output_path,
            "duration_sec": result.duration_sec,
            "error": result.error
        })

        self.dao.update(wb)


# ----------------------------------------------------------------------
# Pipeline Runner
# ----------------------------------------------------------------------
def run_pipeline(input_path):
    """
    Entry function.
    - read project JSON
    - build DAG
    - run worker until done
    """

    raw = read_json(input_path)
    project_name = raw.get("project_name")
    if not project_name:
        raise RuntimeError("Missing project_name in JSON")

    # Set project status
    set_project_status(input_path, ProjectStatus.GENERATING)

    # Parse project JSON
    # Convert project_status string to ProjectStatus enum before parsing
    if "project_status" in raw and isinstance(raw["project_status"], str):
        try:
            raw["project_status"] = ProjectStatus(raw["project_status"])
        except ValueError:
            raw["project_status"] = ProjectStatus.CREATED

    project = from_dict(ProjectJSON, raw)

    # Create pipeline & worker
    pipeline = Pipeline(project_name)
    worker = Worker(pipeline)

    prev_audio = None
    for script_block in project.script:
        print(f"[Pipeline] Build DAG for ScriptBlock {script_block.id}")
        prev_audio = pipeline.build(script_block, prev_audio)

    # Execute
    print("[Pipeline] Start execution…")
    jobs = worker.run_until_complete()
    print(f"[Pipeline] Completed {jobs} jobs")

    # Final status
    dao = WorkingBlockDAO()
    errors = [wb for wb in dao.get_all(project_name) if wb.status == WorkingBlockStatus.ERROR]
    pending = [wb for wb in dao.get_all(project_name) if wb.status == WorkingBlockStatus.PENDING]

    if errors:
        set_project_status(input_path, ProjectStatus.GENERATE_FAILED)
    elif pending:
        set_project_status(input_path, ProjectStatus.GENERATING)
    else:
        set_project_status(input_path, ProjectStatus.RENDERING)

    print("[Pipeline] Finished.")