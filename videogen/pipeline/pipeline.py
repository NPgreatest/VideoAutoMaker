#!/usr/bin/env python3
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

    # ----------------------------------------------------------------------
    # 1. Build WorkingBlocks from ScriptBlock
    # ----------------------------------------------------------------------
    def build(self, script_block: ScriptBlock) -> List[WorkingBlock]:
        working_blocks = []

        # 1. 从数据库恢复 action_id → working_block_id 的映射
        # Get all working blocks for this project, then filter by action_ids in this script_block
        all_blocks = self.dao.get_all(self.project_name)
        script_action_ids = {action.id for action in script_block.actions}
        existing_blocks = [wb for wb in all_blocks if wb.action_id in script_action_ids]
        action_to_wb = {wb.action_id: wb.id for wb in existing_blocks}

        # 2. 遍历 ScriptBlock.actions
        for action in script_block.actions:

            # 如果该 action 已经构建过 → 直接跳过
            if action.id in action_to_wb:
                continue

            # 创建 method 实例
            method = create_method(action.type)

            # auto-fill config.project_name
            action.config = action.config or {}
            if "project_name" not in action.config:
                action.config["project_name"] = self.project_name

            # 3. 创建 WorkingBlock
            wb = method.run(action)

            # 设置 action_id（关键点）
            wb.action_id = action.id

            # 设置 block_id (target_name) 用于路径构建
            # target_name 在 config 中，通常是 ScriptBlock.id
            if "target_name" in action.config:
                wb.block_id = action.config["target_name"]
            else:
                # 如果没有 target_name，使用 action_id 作为后备
                wb.block_id = action.id

            # 4. 构建 prev_wb_ids（DAG）
            prev_wb_ids = []
            for prev_action_id in action.prev_ids:
                prev = action_to_wb.get(prev_action_id)
                if prev:
                    prev_wb_ids.append(prev)
            wb.prev_ids = prev_wb_ids

            # 5. 插入数据库
            if not self.dao.insert(wb):
                print(f"[Pipeline] ⚠️ Failed to insert WorkingBlock {wb.id}")
                continue

            # 6. 更新映射关系
            action_to_wb[action.id] = wb.id
            working_blocks.append(wb)

        return working_blocks

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
        # accumulated_duration_sec
        if result.status == WorkingBlockStatus.SUCCESS:
            if result.duration_sec:
                wb.accumulated_duration_sec += result.duration_sec

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

    # Build DAG from script blocks
    for script_block in project.script:
        print(f"[Pipeline] Build DAG for ScriptBlock {script_block.id}")
        pipeline.build(script_block)

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
