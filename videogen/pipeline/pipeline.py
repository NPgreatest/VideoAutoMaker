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

    def build(self, script_block: ScriptBlock) -> List[WorkingBlock]:
        working_blocks: List[WorkingBlock] = []

        # 1. 先把这个 project 下面所有的 working_block 都取出来
        all_blocks = self.dao.get_all(self.project_name)

        # 当前这个 ScriptBlock 里的 action_id 集合
        script_action_ids = {action.id for action in script_block.actions}

        # 已经存在于 DB 中、且属于这个 ScriptBlock 的 blocks
        existing_blocks = [wb for wb in all_blocks if wb.action_id in script_action_ids]
        action_to_wb = {wb.action_id: wb.id for wb in existing_blocks}

        # ⭐ 找到「整个 project 里」最后一个 fish_audio 的 working_block.id
        last_fish_audio_wb_id = None
        for wb in all_blocks:
            # 这里根据你的 WorkingBlock 字段名来改，
            # screenshot 里列名是 method_name
            if getattr(wb, "method_name", None) == "fish_audio":
                last_fish_audio_wb_id = wb.id

        # ------------------------------------------------------------------
        # 2. 遍历当前 ScriptBlock 的 actions，边构建边设置依赖
        # ------------------------------------------------------------------
        for action in script_block.actions:

            # 如果这个 action 对应的 WorkingBlock 已经存在，跳过构建
            # 但要注意：如果它是 fish_audio，需要把 last_fish_audio_wb_id 更新一下
            if action.id in action_to_wb:
                wb_id = action_to_wb[action.id]

                if action.type == "fish_audio":
                    last_fish_audio_wb_id = wb_id

                continue

            # 创建 method 实例
            method = create_method(action.type)

            # auto-fill config.project_name
            action.config = action.config or {}
            if "project_name" not in action.config:
                action.config["project_name"] = self.project_name

            # ------------------------------------------------------------------
            # 3. 构建 WorkingBlock
            # ------------------------------------------------------------------
            wb = method.run(action)

            # 绑定 action_id
            wb.action_id = action.id

            # block_id 用于路径构建，优先用 target_name
            if "target_name" in action.config:
                wb.block_id = action.config["target_name"]
            else:
                wb.block_id = action.id

            # ------------------------------------------------------------------
            # 4. 构建 prev_wb_ids（DAG 依赖）
            # ------------------------------------------------------------------
            prev_wb_ids: List[str] = []

            # 4.1 先处理 action 自带的 prev_ids（同一行内部的依赖）
            for prev_action_id in action.prev_ids or []:
                prev_wb_id = action_to_wb.get(prev_action_id)
                if prev_wb_id:
                    prev_wb_ids.append(prev_wb_id)

            # 4.2 如果这是一个新的 fish_audio，并且项目里已经有上一条 fish_audio，
            #     就让它依赖上一条 fish_audio 的 working_block.id
            if action.type == "fish_audio" and last_fish_audio_wb_id:
                if last_fish_audio_wb_id not in prev_wb_ids:
                    prev_wb_ids.append(last_fish_audio_wb_id)

            wb.prev_ids = prev_wb_ids

            # ------------------------------------------------------------------
            # 5. 插入数据库
            # ------------------------------------------------------------------
            if not self.dao.insert(wb):
                print(f"[Pipeline] ⚠️ Failed to insert WorkingBlock {wb.id}")
                continue

            # ------------------------------------------------------------------
            # 6. 更新映射关系 / last_fish_audio_wb_id
            # ------------------------------------------------------------------
            action_to_wb[action.id] = wb.id

            if action.type == "fish_audio":
                last_fish_audio_wb_id = wb.id

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
