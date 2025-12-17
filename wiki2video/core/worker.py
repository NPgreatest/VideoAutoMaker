from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Optional, Set

from wiki2video.config.config_vars import WORKINGBLOCK_POLLING_COUNT_MAX, WORKINGBLOCK_POLLING_INTERVAL, \
    WORKINGBLOCK_ERROR_COUNT_MAX
from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.methods.registry import create_method
from wiki2video.core.working_block import WorkingBlockStatus, WorkingBlock
from wiki2video.schema.generation_result_schema import GenerationResult

if TYPE_CHECKING:
    from wiki2video.core.pipeline import Pipeline


# ----------------------------------------------------------------------
# Worker (Executor)
# ----------------------------------------------------------------------
class Worker:

    def __init__(self,project_id: str):
        self.dao = WorkingBlockDAO()
        self.project_id = project_id


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



    def get_next_runnable(self, allowed_methods: Optional[Set[str]] = None):
        """
        Priority-based round-robin scheduling:
        - High priority first
        - Within same priority: pick the task least recently scheduled
        """

        pending = self.dao.get_pending(self.project_id)

        # 1. 过滤 method
        if allowed_methods:
            pending = [wb for wb in pending if wb.method_name in allowed_methods]

        # 对于已经调度过的block，5分钟之后再调度
        have_job = pending != []
        pending = [wb for wb in pending if
                   (wb.last_scheduled_at or float('-inf')) < time.time() - WORKINGBLOCK_POLLING_INTERVAL * 60]


        # 2. 过滤依赖未完成的
        runnable = [wb for wb in pending if self._deps_done(wb)]
        if not runnable:
            return None, have_job

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

        return next_job, have_job


    def run_once(self, allowed_methods: Optional[Set[str]] = None) -> bool:
        wb, have_job = self.get_next_runnable(allowed_methods=allowed_methods)
        if not have_job:
            return False
        if have_job and not wb:
            print("⏳ All job are waiting, polling every 2 minutes")
            time.sleep(120)
            return True

        print(f"[Worker] 🚀 Running job {wb.id} ({wb.method_name})")

        try:
            method = create_method(wb.method_name)
            result = method.poll(wb)
            wb.polling_count += 1
            wb.status = result.status

            if wb.status== WorkingBlockStatus.PENDING and wb.error_count > WORKINGBLOCK_ERROR_COUNT_MAX:
                raise Exception(f"[Worker] too many retry, working block error, {wb.id}, {wb.method_name} failed")
            
        except Exception as e:
            print(f"[Worker] ❌ Exception during job {wb.id}: {e}")

            wb.error_count += 1
            wb.status = WorkingBlockStatus.ERROR
            wb.output_path = None
            result = GenerationResult(
                WorkingBlockStatus.ERROR,
                wb.method_name,
                0,
                str(e)
            )

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
        return True

    def run_until_complete(self, max_iter=999999, allowed_methods: Optional[Set[str]] = None):
        count = 0
        while count < max_iter:
            if not self.run_once(allowed_methods=allowed_methods):
                break
            count += 1
        return count
