"""
Simplified Global Worker for coordinating method-based processing.
This worker polls the SQLite database for pending WorkingBlocks and delegates
processing to the appropriate method instances.
"""

import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.schema import WorkingBlock, WorkingBlockStatus, ScriptBlock
from videogen.methods.registry import create_method


class GlobalWorker:
    """Simplified global worker that delegates to method instances."""
    
    def __init__(self, db_path: Path = None):
        self.dao = WorkingBlockDAO(db_path)
        self.is_running = False
        self.thread = None
        self.poll_interval = 20.0
        self.max_polls_per_task = 600
        
    def _process_working_block(self, working_block: WorkingBlock) -> bool:
        """Process a single WorkingBlock by delegating to the appropriate method."""
        if not working_block.block:
            print(f"[GlobalWorker] WorkingBlock {working_block.working_id} has no block data")
            return False
        
        block = working_block.block
        method_name = block.decision
        
        try:
            # Create method instance
            method = create_method(method_name)
            
            # Check if method supports background processing
            if not method.supports_background_processing():
                print(f"[GlobalWorker] Method {method_name} does not support background processing")
                working_block.status = WorkingBlockStatus.ERROR
                working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                self.dao.update_working_block(working_block)
                return False
            
            print(f"[GlobalWorker] Processing {working_block.working_id} with method {method_name}")
            
            # Delegate processing to the method
            result = method.process_working_block(working_block)
            
            if result is True:
                working_block.status = WorkingBlockStatus.SUCCESS
                print(f"[GlobalWorker] ✅ Successfully processed {working_block.working_id}")
                working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                self.dao.update_working_block(working_block)
                return True
            elif result is False:
                # Actual error - mark as ERROR
                working_block.status = WorkingBlockStatus.ERROR
                print(f"[GlobalWorker] ❌ Failed to process {working_block.working_id}")
                working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                self.dao.update_working_block(working_block)
                return False
            else:
                # result is None - still processing, keep as PENDING
                print(f"[GlobalWorker] ⏳ Task {working_block.working_id} still processing...")
                # Update working block with latest block data but keep status as PENDING
                working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                self.dao.update_working_block(working_block)
                return None  # Indicate still processing
            
        except Exception as e:
            print(f"[GlobalWorker] ❌ Error processing {working_block.working_id}: {e}")
            working_block.status = WorkingBlockStatus.ERROR
            working_block.modify_time = datetime.utcnow().isoformat() + "Z"
            self.dao.update_working_block(working_block)
            return False
    
    def _worker_loop(self):
        """Main worker loop that polls for pending WorkingBlocks."""
        print("[GlobalWorker] Starting worker loop...")
        idle_rounds = 0
        
        while self.is_running:
            try:
                # Get all pending working blocks
                pending_blocks = self.dao.get_pending_working_blocks()
                
                if not pending_blocks:
                    idle_rounds += 1
                    print(f"[GlobalWorker] No pending blocks ({idle_rounds}/3)...")
                    if idle_rounds >= 3:
                        print("[GlobalWorker] ✅ All tasks finished.")
                        break
                    time.sleep(self.poll_interval)
                    continue
                else:
                    idle_rounds = 0
                
                total = len(pending_blocks)
                print(f"[GlobalWorker] Processing {total} pending blocks...")
                
                for working_block in pending_blocks:
                    if not self.is_running:
                        break
                    
                    # Check if task has exceeded max polls
                    if working_block.poll_count >= self.max_polls_per_task:
                        print(f"[GlobalWorker] ⏰ Task {working_block.working_id} timed out")
                        working_block.status = WorkingBlockStatus.ERROR
                        working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                        self.dao.update_working_block(working_block)
                        continue
                    
                    # Increment poll count
                    working_block.poll_count += 1
                    working_block.modify_time = datetime.utcnow().isoformat() + "Z"
                    self.dao.update_working_block(working_block)
                    
                    # Process the working block
                    self._process_working_block(working_block)
                
                print(f"[GlobalWorker] Sleep {self.poll_interval}s...")
                time.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"[GlobalWorker] Error in worker loop: {e}")
                time.sleep(self.poll_interval)
        
        print("[GlobalWorker] Worker loop stopped.")
    
    def start(self):
        """Start the global worker."""
        if self.is_running:
            print("[GlobalWorker] Worker is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print("[GlobalWorker] Worker started")
    
    def stop(self):
        """Stop the global worker."""
        if not self.is_running:
            print("[GlobalWorker] Worker is not running")
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("[GlobalWorker] Worker stopped")
    
    def wait_for_completion(self, project_id: str = None, timeout_seconds: int = 3000):
        """Wait for all pending WorkingBlocks to complete."""
        start_time = time.time()
        print(f"[GlobalWorker] Waiting for completion (timeout: {timeout_seconds}s)...")
        
        while time.time() - start_time < timeout_seconds:
            pending_blocks = self.dao.get_pending_working_blocks()
            if project_id:
                pending_blocks = [wb for wb in pending_blocks if wb.project_id == project_id]
            
            if not pending_blocks:
                print("[GlobalWorker] ✅ All tasks completed!")
                return True
            
            print(f"[GlobalWorker] {len(pending_blocks)} tasks still pending...")
            time.sleep(20)
        
        print(f"[GlobalWorker] ⏰ Timeout waiting for completion")
        return False
    
    def get_status_summary(self) -> Dict[str, int]:
        """Get a summary of WorkingBlock statuses."""
        all_blocks = self.dao.get_all_working_blocks()
        summary = {
            "pending": 0,
            "success": 0,
            "error": 0,
            "total": len(all_blocks)
        }
        
        for block in all_blocks:
            if block.status == WorkingBlockStatus.PENDING:
                summary["pending"] += 1
            elif block.status == WorkingBlockStatus.SUCCESS:
                summary["success"] += 1
            elif block.status == WorkingBlockStatus.ERROR:
                summary["error"] += 1
        
        return summary


# Global worker instance
_global_worker: Optional[GlobalWorker] = None
_worker_lock = threading.Lock()


def get_global_worker(db_path: Path = None) -> GlobalWorker:
    """Get the global worker instance (singleton)."""
    global _global_worker
    
    with _worker_lock:
        if _global_worker is None:
            _global_worker = GlobalWorker(db_path)
        return _global_worker


def start_global_worker(db_path: Path = None):
    """Start the global worker."""
    worker = get_global_worker(db_path)
    worker.start()


def stop_global_worker():
    """Stop the global worker."""
    global _global_worker
    if _global_worker:
        _global_worker.stop()


def wait_for_global_worker_completion(project_id: str = None, timeout_seconds: int = 3000) -> bool:
    """Wait for the global worker to complete all tasks."""
    worker = get_global_worker()
    return worker.wait_for_completion(project_id, timeout_seconds)