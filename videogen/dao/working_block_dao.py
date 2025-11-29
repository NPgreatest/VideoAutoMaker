import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus


class WorkingBlockDAO:
    """SQLite DAO for WorkingBlock management (with priority scheduling support)."""

    _lock = threading.Lock()

    BASE_COLUMNS = (
        "id, project_name, method_name, status, retries, "
        "prev_ids, output_path, accumulated_duration_sec, "
        "block_id, action_index, "
        "config_json, result_json, "
        "priority, last_scheduled_at, "
        "create_time, modify_time"
    )

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path("db/working_blocks.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    # -----------------------------------------------------------
    #  INIT + MIGRATIONS
    # -----------------------------------------------------------
    def _init_database(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS working_blocks (
                    id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    retries INTEGER DEFAULT 0,
                    prev_ids TEXT,
                    output_path TEXT,
                    accumulated_duration_sec REAL DEFAULT 0.0,
                    block_id TEXT,
                    action_index INTEGER,
                    config_json TEXT DEFAULT '',
                    result_json TEXT DEFAULT '',
                    priority INTEGER DEFAULT 10,
                    last_scheduled_at REAL DEFAULT 0,
                    create_time TEXT,
                    modify_time TEXT
                )
            """)

            # Auto-migrate missing columns for legacy DB
            self._ensure_column(cursor, "priority", "INTEGER DEFAULT 10")
            self._ensure_column(cursor, "last_scheduled_at", "REAL DEFAULT 0")
            self._ensure_column(cursor, "block_id", "TEXT")
            self._ensure_column(cursor, "action_index", "INTEGER")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_project ON working_blocks(project_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON working_blocks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON working_blocks(priority)")

            conn.commit()
            conn.close()

    def _ensure_column(self, cursor, col_name: str, col_type: str):
        cursor.execute("PRAGMA table_info(working_blocks)")
        cols = [row[1] for row in cursor.fetchall()]
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE working_blocks ADD COLUMN {col_name} {col_type}")

    # -----------------------------------------------------------
    #  INTERNAL UTILITIES
    # -----------------------------------------------------------
    def _decode_row(self, row) -> WorkingBlock:
        """Convert SQLite row tuple → WorkingBlock."""
        (
            id, project_name, method_name, status, retries,
            prev_ids_raw, output_path, acc_dur,
            block_id, action_index,
            config_json, result_json,
            priority, last_scheduled_at,
            create_time, modify_time
        ) = row

        try:
            prev_ids = json.loads(prev_ids_raw) if prev_ids_raw else []
        except:
            prev_ids = []

        return WorkingBlock(
            id=id,
            project_name=project_name,
            method_name=method_name,
            status=WorkingBlockStatus(status),
            retries=retries or 0,
            prev_ids=prev_ids,
            output_path=output_path,
            accumulated_duration_sec=acc_dur or 0.0,
            block_id=block_id,
            action_index=action_index,
            config_json=config_json or "",
            result_json=result_json or "",
            priority=priority if priority is not None else 10,
            last_scheduled_at=last_scheduled_at if last_scheduled_at is not None else 0,
            create_time=create_time,
            modify_time=modify_time
        )

    # -----------------------------------------------------------
    #  CRUD
    # -----------------------------------------------------------
    def insert(self, wb: WorkingBlock) -> bool:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                wb.create_time = wb.create_time or now
                wb.modify_time = wb.modify_time or now

                cursor.execute(f"""
                    INSERT INTO working_blocks
                    (id, project_name, method_name, status, retries,
                     prev_ids, output_path, accumulated_duration_sec,
                     block_id, action_index, config_json, result_json,
                     priority, last_scheduled_at,
                     create_time, modify_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wb.id,
                    wb.project_name,
                    wb.method_name,
                    wb.status.value,
                    wb.retries,
                    json.dumps(wb.prev_ids or []),
                    wb.output_path,
                    wb.accumulated_duration_sec,
                    wb.block_id,
                    wb.action_index,
                    wb.config_json,
                    wb.result_json,
                    wb.priority or 10,
                    wb.last_scheduled_at or 0,
                    wb.create_time,
                    wb.modify_time
                ))

                conn.commit()
                return True
            finally:
                conn.close()

    def update(self, wb: WorkingBlock) -> bool:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                wb.modify_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"

                cursor.execute(f"""
                    UPDATE working_blocks SET
                        project_name=?, method_name=?, status=?, retries=?,
                        prev_ids=?, output_path=?, accumulated_duration_sec=?,
                        block_id=?, action_index=?, config_json=?, result_json=?,
                        priority=?, last_scheduled_at=?,
                        modify_time=?
                    WHERE id=?
                """, (
                    wb.project_name,
                    wb.method_name,
                    wb.status.value,
                    wb.retries,
                    json.dumps(wb.prev_ids or []),
                    wb.output_path,
                    wb.accumulated_duration_sec,
                    wb.block_id,
                    wb.action_index,
                    wb.config_json,
                    wb.result_json,
                    wb.priority,
                    wb.last_scheduled_at,
                    wb.modify_time,
                    wb.id
                ))

                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def delete(self, working_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM working_blocks WHERE id = ?", (working_id,))
            conn.commit()
            ok = cursor.rowcount > 0
            conn.close()
            return ok

    # -----------------------------------------------------------
    #  QUERY APIS
    # -----------------------------------------------------------
    def get_by_id(self, working_id: str) -> Optional[WorkingBlock]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {self.BASE_COLUMNS} FROM working_blocks WHERE id=?
        """, (working_id,))
        row = cursor.fetchone()
        conn.close()
        return self._decode_row(row) if row else None

    def get_all(self, project_name: Optional[str] = None) -> List[WorkingBlock]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if project_name:
            cursor.execute(f"""
                SELECT {self.BASE_COLUMNS}
                FROM working_blocks
                WHERE project_name=?
                ORDER BY create_time ASC
            """, (project_name,))
        else:
            cursor.execute(f"""
                SELECT {self.BASE_COLUMNS}
                FROM working_blocks
                ORDER BY create_time ASC
            """)

        rows = cursor.fetchall()
        conn.close()

        return [self._decode_row(row) for row in rows]

    def get_pending(self, project_name: str = None) -> List[WorkingBlock]:
        all_blocks = self.get_all(project_name)
        return [wb for wb in all_blocks if wb.status == WorkingBlockStatus.PENDING]

    def get_completed(self, project_name: str = None) -> List[WorkingBlock]:
        all_blocks = self.get_all(project_name)
        return [wb for wb in all_blocks
                if wb.status in (WorkingBlockStatus.SUCCESS, WorkingBlockStatus.ERROR)]

    def get_by_block_id(self, project_name: str, block_id: str) -> List[WorkingBlock]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_name=? AND block_id=?
            ORDER BY action_index ASC
        """, (project_name, block_id))
        rows = cursor.fetchall()
        conn.close()
        return [self._decode_row(r) for r in rows]
    # -----------------------------------------------------------
    # BACKWARD COMPATIBILITY — Legacy DAO API
    # Keep ALL old API names so that pipeline/UI code never breaks.
    # -----------------------------------------------------------

    # old: get_working_block(id)
    def get_working_block(self, working_id: str):
        return self.get_by_id(working_id)

    # old: update_working_block(block)
    def update_working_block(self, working_block: WorkingBlock):
        return self.update(working_block)

    # old: delete_working_block(id)
    def delete_working_block(self, working_id: str):
        return self.delete(working_id)

    # old: create_working_block(block)
    def create_working_block(self, block: WorkingBlock):
        return self.insert(block)

    # old: get_all_working_blocks(project_name)
    def get_all_working_blocks(self, project_name: str = None):
        return self.get_all(project_name)

    # old: get_pending_working_blocks()
    def get_pending_working_blocks(self):
        return self.get_pending()

    # old: get_completed_working_blocks()
    def get_completed_working_blocks(self):
        return self.get_completed()

    # old: get_by_method_name(project_name, block_id, method_name)
    def get_by_method_name(self, project_name: str, block_id: str, method_name: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_name = ?
              AND block_id = ?
              AND method_name = ?
            ORDER BY action_index ASC
            LIMIT 1
        """, (project_name, block_id, method_name))
        row = cursor.fetchone()
        conn.close()
        return self._decode_row(row) if row else None

    # old: get_by_action_index(project_name, block_id, action_index)
    def get_by_action_index(self, project_name: str, block_id: str, action_index: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_name = ?
              AND block_id = ?
              AND action_index = ?
            LIMIT 1
        """, (project_name, block_id, action_index))
        row = cursor.fetchone()
        conn.close()
        return self._decode_row(row) if row else None
