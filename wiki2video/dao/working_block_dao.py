import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional

from wiki2video.db.init_db import init_database_if_needed
from wiki2video.core.paths import get_db_path
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus

DB_PATH = Path("db/working_blocks.db")

class WorkingBlockDAO:

    _lock = threading.Lock()

    BASE_COLUMNS = (
        "id, project_id, method_name, status, "
        "polling_count, error_count, priority, "
        "prev_ids, output_path, accumulated_duration_sec, "
        "block_id, action_index, config_json, result_json, "
        "create_time, last_scheduled_at"
    )


    def __init__(self, db_path: Path | None = None):
        init_database_if_needed()
        self.db_path = db_path or get_db_path()

    # ---------------------------------------------------------
    # Internal util: row → WorkingBlock
    # ---------------------------------------------------------
    def _row_to_wb(self, row: tuple) -> WorkingBlock:
        (
            id, project_id, method_name, status,
            polling_count, error_count, priority,
            prev_ids_raw, output_path, acc_dur,
            block_id, action_index, config_json, result_json,
            create_time, last_scheduled_at
        ) = row

        try:
            prev_ids = json.loads(prev_ids_raw) if prev_ids_raw else []
        except json.JSONDecodeError:
            prev_ids = []

        return WorkingBlock(
            id=id,
            project_id=project_id,
            method_name=method_name,
            status=WorkingBlockStatus(status),

            polling_count=polling_count,
            error_count=error_count,
            priority=priority,

            prev_ids=prev_ids,
            output_path=output_path,
            accumulated_duration_sec=acc_dur or 0.0,

            block_id=block_id,
            action_index=action_index,

            config_json=config_json or "",
            result_json=result_json or "",

            create_time=create_time,
            last_scheduled_at=last_scheduled_at
        )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------
    def insert(self, wb: WorkingBlock) -> bool:
        """
        Insert a new WorkingBlock.
        Returns True if inserted, False if primary key conflict.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cur = conn.cursor()
                cur.execute(f"""
                    INSERT INTO working_blocks
                    (id, project_id, method_name, status,
                     polling_count, error_count, priority,
                     prev_ids, output_path, accumulated_duration_sec,
                     block_id, action_index, config_json, result_json,
                     create_time, last_scheduled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wb.id,
                    wb.project_id,
                    wb.method_name,
                    wb.status.value,
                    wb.polling_count,
                    wb.error_count,
                    wb.priority,
                    json.dumps(wb.prev_ids),
                    wb.output_path,
                    wb.accumulated_duration_sec,
                    wb.block_id,
                    wb.action_index,
                    wb.config_json,
                    wb.result_json,
                    wb.create_time,
                    wb.last_scheduled_at
                ))
                conn.commit()
                return True

            except sqlite3.IntegrityError:
                return False

            finally:
                conn.close()

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------
    def get_by_id(self, block_id: str) -> Optional[WorkingBlock]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        row = cur.execute(
            f"SELECT {self.BASE_COLUMNS} FROM working_blocks WHERE id=?",
            (block_id,)
        ).fetchone()
        conn.close()
        return self._row_to_wb(row) if row else None

    def get_all(self, project_id: Optional[str] = None) -> List[WorkingBlock]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if project_id:
            rows = cur.execute(
                f"SELECT {self.BASE_COLUMNS} FROM working_blocks "
                "WHERE project_id=? ORDER BY create_time ASC",
                (project_id,)
            ).fetchall()
        else:
            rows = cur.execute(
                f"SELECT {self.BASE_COLUMNS} FROM working_blocks ORDER BY create_time ASC"
            ).fetchall()

        conn.close()
        return [self._row_to_wb(r) for r in rows]

    def get_pending(self, project_id: str) -> List[WorkingBlock]:
        """
        Get all PENDING blocks for a given project_id.
        Highly optimized to match schema index on (project_id, status).
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute(
            f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_id=? AND status=?
            """,
            (project_id, WorkingBlockStatus.PENDING.value)
        ).fetchall()

        conn.close()
        return [self._row_to_wb(r) for r in rows]

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------
    def update(self, wb: WorkingBlock) -> bool:
        """
        Update all fields of a WorkingBlock by id.
        Returns True if updated, False if id does not exist.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute(f"""
                UPDATE working_blocks SET
                    project_id=?, method_name=?, status=?,
                    polling_count=?, error_count=?, priority=?,
                    prev_ids=?, output_path=?, accumulated_duration_sec=?,
                    block_id=?, action_index=?, config_json=?, result_json=?,
                    create_time=?, last_scheduled_at=?
                WHERE id=?
            """, (
                wb.project_id,
                wb.method_name,
                wb.status.value,

                wb.polling_count,
                wb.error_count,
                wb.priority,

                json.dumps(wb.prev_ids),
                wb.output_path,
                wb.accumulated_duration_sec,

                wb.block_id,
                wb.action_index,
                wb.config_json,
                wb.result_json,

                wb.create_time,
                wb.last_scheduled_at,

                wb.id
            ))

            conn.commit()
            updated = cur.rowcount > 0
            conn.close()
            return updated

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------
    def delete(self, block_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("DELETE FROM working_blocks WHERE id=?", (block_id,))
            conn.commit()
            deleted = cur.rowcount > 0

            conn.close()
            return deleted

    # ---------------------------------------------------------
    # Specialized query utilities
    # ---------------------------------------------------------
    def get_by_block(self, project_id: str, block_id: str) -> List[WorkingBlock]:
        """Get all actions for a script block (e.g., L1)."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_id=? AND block_id=?
            ORDER BY action_index ASC
            """,
            (project_id, block_id)
        ).fetchall()
        conn.close()
        return [self._row_to_wb(r) for r in rows]

    def get_latest_by_method(self, project_id: str, method_name: str) -> Optional[WorkingBlock]:
        """Get the most recent block executed with a given method."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            f"""
            SELECT {self.BASE_COLUMNS}
            FROM working_blocks
            WHERE project_id=? AND method_name=?
            ORDER BY create_time DESC
            LIMIT 1
            """,
            (project_id, method_name)
        ).fetchone()
        conn.close()
        return self._row_to_wb(row) if row else None
