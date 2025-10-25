from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from videogen.methods.text_video_silicon.constants import (
    POLL_INTERVAL_SEC, MAX_POLLS_PER_TASK,
    STATUS_SUCCEED, STATUS_ERROR, NON_TERMINAL, TERMINAL,
)
from videogen.methods.text_video_silicon.sf_api import check_status, download_to
from videogen.methods.text_video_silicon.store import TaskCSV
from videogen.methods.text_video_silicon.utils import resize_video_duration


class WorkerManager:
    """Manages background worker threads for polling video generation results."""
    
    def __init__(self, store: TaskCSV, log_dir: Path = Path("./log")):
        self.store = store
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Thread management
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Track submitted tasks
        self._submitted_tasks: Set[str] = set()
        self._completed_tasks: Set[str] = set()
        
    def _setup_logging(self):
        """Setup logging to ./log folder."""
        log_file = self.log_dir / f"worker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Create logger
        self.logger = logging.getLogger(f"worker_{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def start_worker(self):
        """Start the background worker thread."""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                self.logger.info("Worker already running")
                return
                
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop, 
                daemon=True, 
                name="video-worker"
            )
            self._worker_thread.start()
            self.logger.info("Background worker started")
    
    def stop_worker(self):
        """Stop the background worker thread."""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                self._stop_event.set()
                self._worker_thread.join(timeout=5.0)
                self.logger.info("Background worker stopped")
    
    def submit_task(self, request_id: str):
        """Register a new task for tracking."""
        with self._lock:
            self._submitted_tasks.add(request_id)
            self.logger.info(f"Task {request_id} submitted for tracking")
    
    def get_completion_status(self) -> Dict[str, int]:
        """Get completion status of all tracked tasks."""
        with self._lock:
            total = len(self._submitted_tasks)
            completed = len(self._completed_tasks)
            return {
                "total": total,
                "completed": completed,
                "pending": total - completed
            }
    
    def wait_for_all_completion(self, timeout_seconds: int = 1800) -> bool:
        """Wait for all submitted tasks to complete."""
        self.logger.info(f"Waiting for {len(self._submitted_tasks)} tasks to complete...")
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            status = self.get_completion_status()
            self.logger.info(f"Progress: {status['completed']}/{status['total']} completed")
            
            if status['pending'] == 0:
                self.logger.info("All tasks completed!")
                return True
                
            time.sleep(5.0)  # Check every 5 seconds
        
        self.logger.warning(f"Timeout waiting for completion after {timeout_seconds}s")
        return False
    
    def _worker_loop(self):
        """Main worker loop that polls for task completion."""
        self.logger.info("Worker loop started")
        idle_rounds = 0
        
        while not self._stop_event.is_set():
            try:
                rows = self.store.get_all()
                now = time.time()
                
                if not rows:
                    self.logger.debug("No tasks in CSV. Sleeping...")
                    time.sleep(POLL_INTERVAL_SEC)
                    continue
                
                total = len(rows)
                done = sum(1 for r in rows if r.get("status") in TERMINAL)
                self.logger.info(f"Checking {total} tasks ({done} done, {total - done} active)...")
                
                if done == total:
                    idle_rounds += 1
                    self.logger.info(f"All tasks complete ({idle_rounds}/3)...")
                    if idle_rounds >= 3:
                        self.logger.info("All tasks finished. Checking for repairs...")
                        self._check_and_resize_missing_final_videos()
                        break
                    time.sleep(POLL_INTERVAL_SEC)
                    continue
                else:
                    idle_rounds = 0
                
                # Process each task
                for row in rows:
                    if self._stop_event.is_set():
                        break
                    self._process_task(row, now)
                
                # Update completed tasks tracking
                self._update_completed_tasks(rows)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(POLL_INTERVAL_SEC)
            
            time.sleep(POLL_INTERVAL_SEC)
        
        self.logger.info("Worker loop ended")
    
    def _process_task(self, row: Dict[str, str], now: float):
        """Process a single task."""
        rid = row.get("request_id", "")
        status = row.get("status", "")
        poll_cnt = int(row.get("poll_count", "0"))
        
        if status in TERMINAL:
            return  # Already done
        
        if poll_cnt >= MAX_POLLS_PER_TASK:
            self.logger.warning(f"Task {rid} exceeded max polls, marking as error")
            row.update({
                "status": STATUS_ERROR,
                "error": "Max polls exceeded",
                "updated_ts": str(now),
            })
            self.store.upsert(row)
            return
        
        try:
            resp = check_status(rid)
            new_status = resp.get("status", status)
            
            if new_status == STATUS_SUCCEED:
                self._handle_successful_task(row, resp, now)
            elif new_status in NON_TERMINAL:
                self._handle_non_terminal_task(row, new_status, now, poll_cnt)
            else:
                self._handle_terminal_error(row, new_status, resp, now, poll_cnt)
                
        except Exception as e:
            self.logger.error(f"Error processing task {rid}: {e}")
            row.update({
                "status": STATUS_ERROR,
                "error": f"Processing error: {e}",
                "updated_ts": str(now),
                "poll_count": str(poll_cnt + 1),
            })
            self.store.upsert(row)
    
    def _handle_successful_task(self, row: Dict[str, str], resp: Dict, now: float):
        """Handle a successfully completed task."""
        rid = row.get("request_id", "")
        try:
            # Get download URL from API response
            videos = (resp.get("results") or {}).get("videos") or []
            url = videos[0].get("url") if videos else None
            if not url:
                raise Exception("Succeed but no video url")
            
            # Setup paths
            workdir = Path(row.get("workdir", ""))
            if not workdir:
                raise Exception("No workdir specified for task")
            
            project_dir = workdir / "project" / row.get("project", "")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            target_name = row.get("target_name", rid)
            raw_mp4 = project_dir / f"{target_name}_raw.mp4"
            final_mp4 = project_dir / f"{target_name}.mp4"
            
            # Download raw video
            download_to(url, raw_mp4)
            if not raw_mp4.exists():
                raise Exception("Download failed or file not found")
            
            # Resize to target duration
            duration = float(row.get("duration", "5.0"))
            new_dur = resize_video_duration(raw_mp4, final_mp4, duration)
            
            # Update row
            row.update({
                "status": STATUS_SUCCEED,
                "output_path": str(final_mp4),
                "source_url": url,
                "updated_ts": str(now),
            })
            self.store.upsert(row)
            
            # Save metadata
            self._save_task_metadata(rid, row, resp)
            
            self.logger.info(f"✅ Task {rid} completed successfully: {final_mp4}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling successful task {rid}: {e}")
            row.update({
                "status": STATUS_ERROR,
                "error": f"Success handling error: {e}",
                "updated_ts": str(now),
            })
            self.store.upsert(row)
    
    def _handle_non_terminal_task(self, row: Dict[str, str], new_status: str, now: float, poll_cnt: int):
        """Handle a task that's still in progress."""
        row.update({
            "status": new_status,
            "updated_ts": str(now),
            "poll_count": str(poll_cnt + 1),
        })
        self.store.upsert(row)
    
    def _handle_terminal_error(self, row: Dict[str, str], new_status: str, resp: Dict, now: float, poll_cnt: int):
        """Handle a task that failed."""
        row.update({
            "status": new_status,
            "error": resp.get("error", ""),
            "updated_ts": str(now),
            "poll_count": str(poll_cnt + 1),
        })
        self.store.upsert(row)
        self.logger.warning(f"Task {row.get('request_id')} failed with status: {new_status}")
    
    def _save_task_metadata(self, request_id: str, row: Dict[str, str], resp: Dict):
        """Save task metadata to log folder."""
        try:
            meta_data = {
                "request_id": request_id,
                "project": row.get("project", ""),
                "target_name": row.get("target_name", ""),
                "prompt": row.get("prompt", ""),
                "model": row.get("model", ""),
                "status": row.get("status", ""),
                "output_path": row.get("output_path", ""),
                "source_url": row.get("source_url", ""),
                "duration": row.get("duration", ""),
                "created_ts": row.get("created_ts", ""),
                "updated_ts": row.get("updated_ts", ""),
                "poll_count": row.get("poll_count", ""),
                "api_response": resp,
            }
            
            meta_file = self.log_dir / f"task_{request_id}_meta.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Metadata saved: {meta_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving metadata for {request_id}: {e}")
    
    def _update_completed_tasks(self, rows: List[Dict[str, str]]):
        """Update the set of completed tasks."""
        with self._lock:
            for row in rows:
                rid = row.get("request_id", "")
                status = row.get("status", "")
                
                if rid in self._submitted_tasks and status in TERMINAL and rid not in self._completed_tasks:
                    self._completed_tasks.add(rid)
                    self.logger.info(f"Task {rid} marked as completed with status: {status}")
    
    def _check_and_resize_missing_final_videos(self):
        """Check for raw-only videos and resize them."""
        try:
            rows = self.store.get_all()
            fixed_count = 0
            
            for row in rows:
                if row.get("status") != STATUS_SUCCEED:
                    continue
                    
                output_path = row.get("output_path", "")
                if not output_path or not Path(output_path).exists():
                    continue
                
                # Check if it's a raw video that needs resizing
                if "_raw" in output_path:
                    try:
                        duration = float(row.get("duration", "5.0"))
                        final_path = resize_video_duration(output_path, duration)
                        
                        # Update the row with the final path
                        row["output_path"] = str(final_path)
                        self.store.upsert(row)
                        fixed_count += 1
                        
                        self.logger.info(f"Fixed raw video: {output_path} -> {final_path}")
                        
                    except Exception as e:
                        self.logger.error(f"Error fixing raw video {output_path}: {e}")
            
            if fixed_count > 0:
                self.logger.info(f"Repair completed. Fixed {fixed_count} videos.")
            else:
                self.logger.info("No videos needed repair.")
                
        except Exception as e:
            self.logger.error(f"Error during repair check: {e}")


# Global worker manager instance
_worker_manager: Optional[WorkerManager] = None
_manager_lock = threading.Lock()


def get_worker_manager(store: TaskCSV, log_dir: Path = Path("./log")) -> WorkerManager:
    """Get or create the global worker manager."""
    global _worker_manager
    
    with _manager_lock:
        if _worker_manager is None:
            _worker_manager = WorkerManager(store, log_dir)
        return _worker_manager


def start_global_worker(store: TaskCSV, log_dir: Path = Path("./log")) -> WorkerManager:
    """Start the global worker manager."""
    manager = get_worker_manager(store, log_dir)
    manager.start_worker()
    return manager
