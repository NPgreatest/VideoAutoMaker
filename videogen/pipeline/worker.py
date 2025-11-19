from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set
from datetime import datetime

from videogen.methods.registry import create_method
from videogen.pipeline.working_block import WorkingBlockStatus
from videogen.pipeline.path_utils import get_action_output_dir, get_meta_file_path

if TYPE_CHECKING:
    from videogen.pipeline.pipeline import Pipeline


# ----------------------------------------------------------------------
# Worker (Executor)
# ----------------------------------------------------------------------
class Worker:
    """
    Worker is a pure executor:
    - fetch next job from pipeline
    - run method.poll()
    - pass result back to pipeline.update_job()
    - create action directories and write meta.json
    """

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def _ensure_action_dir(self, wb) -> Path:
        """
        Ensure the action output directory exists and return it.
        
        Args:
            wb: WorkingBlock instance
            
        Returns:
            Path to action output directory
        """
        # Get project_root from config
        config_dict = json.loads(wb.config_json) if wb.config_json else {}
        workdir = Path(config_dict.get("workdir", "."))
        project_root = workdir.resolve()
        
        # Get block_id (fallback to working_block.id if not set)
        block_id = wb.block_id or wb.id
        
        # Create action directory
        action_dir = get_action_output_dir(
            project_root=project_root,
            project_name=wb.project_name,
            block_id=block_id,
            method_name=wb.method_name,
            working_block_id=wb.id
        )
        action_dir.mkdir(parents=True, exist_ok=True)
        
        return action_dir

    def _write_meta_json(self, wb, action_dir: Path, result) -> None:
        """
        Write meta.json file for the action.
        
        Args:
            wb: WorkingBlock instance
            action_dir: Action output directory
            result: GenerationResult
        """
        config_dict = json.loads(wb.config_json) if wb.config_json else {}
        
        # Determine output file name
        output_file_name = None
        if result.output_path:
            output_path = Path(result.output_path)
            if output_path.exists():
                output_file_name = output_path.name
        
        meta = {
            "working_block_id": wb.id,
            "method": wb.method_name,
            "block_id": wb.block_id or wb.id,
            "config": config_dict,
            "output": output_file_name,
            "status": result.status.value,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "duration_sec": result.duration_sec,
            "error": result.error
        }
        
        meta_path = get_meta_file_path(action_dir)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f"[Worker] ✅ Wrote meta.json to {meta_path}")

    def run_once(self, allowed_methods: Optional[Set[str]] = None) -> bool:
        wb = self.pipeline.get_next_runnable(allowed_methods=allowed_methods)
        if not wb:
            return False

        print(f"[Worker] 🚀 Running job {wb.id} ({wb.method_name})")

        # Ensure action directory exists
        action_dir = self._ensure_action_dir(wb)

        try:
            method = create_method(wb.method_name)
            result = method.poll(wb)
            
            # Write meta.json after method execution
            self._write_meta_json(wb, action_dir, result)
        except Exception as e:
            print(f"[Worker] ❌ Exception during job {wb.id}: {e}")

            # convert to error result
            class Err:
                status = WorkingBlockStatus.ERROR
                output_path = None
                duration_sec = None
                error = str(e)

            # Write meta.json even for errors
            self._write_meta_json(wb, action_dir, Err())

            self.pipeline.update_job(wb, Err())
            return True

        # update pipeline db
        self.pipeline.update_job(wb, result)
        return True

    def run_until_complete(self, max_iter=999999, allowed_methods: Optional[Set[str]] = None):
        count = 0
        while count < max_iter:
            if not self.run_once(allowed_methods=allowed_methods):
                break
            count += 1
        return count
