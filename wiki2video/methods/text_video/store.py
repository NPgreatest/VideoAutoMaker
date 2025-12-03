import csv, threading, time
from pathlib import Path
from typing import Dict, List, Optional

class TaskCSV:
    _lock = threading.Lock()  # fine now, no nested locks

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["request_id", "status", "output_path"])
                writer.writeheader()

    def get_all(self) -> List[Dict[str, str]]:
        if not self.db_path.exists():
            return []
        with open(self.db_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row for row in reader]

    def upsert(self, row: Dict[str, str]) -> None:
        with self._lock:
            rows = self.get_all()
            rid = row.get("request_id")
            updated = False
            for r in rows:
                if r.get("request_id") == rid:
                    r.update(row)
                    updated = True
                    break
            if not updated:
                rows.append(row)

            fieldnames = sorted(set().union(*(r.keys() for r in rows)))
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
                f.flush()

        print(f"[TaskCSV] ✅ Upserted {rid} (status={row.get('status')})")

    def get_task(self, request_id: str) -> Optional[Dict[str, str]]:
        """Get a specific task by request_id"""
        rows = self.get_all()
        for row in rows:
            if row.get("request_id") == request_id:
                return row
        return None

    def wait_for_completion(self, request_id: str, timeout_seconds: int = 300, poll_interval: float = 2.0) -> Optional[Dict[str, str]]:
        """
        Wait for a task to complete (status in TERMINAL states).
        Returns the final task data or None if timeout/not found.
        """
        from .constants import TERMINAL
        
        start_time = time.time()
        print(f"[TaskCSV] Waiting for task {request_id} to complete...")
        
        while time.time() - start_time < timeout_seconds:
            task = self.get_task(request_id)
            if not task:
                print(f"[TaskCSV] Task {request_id} not found")
                return None
            
            status = task.get("status", "")
            if status in TERMINAL:
                print(f"[TaskCSV] Task {request_id} completed with status: {status}")
                return task
            
            print(f"[TaskCSV] Task {request_id} still {status}, waiting...")
            time.sleep(poll_interval)
        
        print(f"[TaskCSV] Timeout waiting for task {request_id}")
        return None
