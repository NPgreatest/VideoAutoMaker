"""
SQLite DAO for WorkingBlock storage and management.
Replaces the CSV-based storage with a proper SQLite database.
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus


class WorkingBlockDAO:
    """SQLite DAO for WorkingBlock management."""
    
    _lock = threading.Lock()
    SELECT_FIELDS = (
        "id, project_name, method_name, status, retries, "
        "prev_ids, output_path, accumulated_duration_sec, block_id, action_index, "
        "config_json, result_json, create_time, modify_time"
    )
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path("db/working_blocks.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _ensure_block_id_column(self, cursor):
        """Ensure the block_id column exists for legacy databases."""
        cursor.execute("PRAGMA table_info(working_blocks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "block_id" not in columns:
            cursor.execute("ALTER TABLE working_blocks ADD COLUMN block_id TEXT")
    
    def _ensure_action_index_column(self, cursor):
        """Ensure the action_index column exists for legacy databases."""
        cursor.execute("PRAGMA table_info(working_blocks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "action_index" not in columns:
            cursor.execute("ALTER TABLE working_blocks ADD COLUMN action_index INTEGER")
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create working_blocks table with new schema
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
                    create_time TEXT,
                    modify_time TEXT
                )
            """)
            
            # Ensure new columns exist for legacy DBs
            self._ensure_block_id_column(cursor)
            self._ensure_action_index_column(cursor)
            
            # Drop old action_id column if exists (migration)
            cursor.execute("PRAGMA table_info(working_blocks)")
            columns = [row[1] for row in cursor.fetchall()]
            if "action_id" in columns:
                # SQLite doesn't support DROP COLUMN directly, so we'll create a new table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS working_blocks_new (
                        id TEXT PRIMARY KEY,
                        project_name TEXT NOT NULL,
                        method_name TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        retries INTEGER DEFAULT 0,
                        prev_ids TEXT,
                        output_path TEXT,
                        accumulated_duration_sec REAL DEFAULT 0.0,
                        block_id TEXT,
                        config_json TEXT DEFAULT '',
                        result_json TEXT DEFAULT '',
                        create_time TEXT,
                        modify_time TEXT
                    )
                """)
                cursor.execute("""
                    INSERT INTO working_blocks_new 
                    (id, project_name, method_name, status, retries, prev_ids, output_path, 
                     accumulated_duration_sec, block_id, config_json, result_json, create_time, modify_time)
                    SELECT id, project_name, method_name, status, retries, prev_ids, output_path,
                           accumulated_duration_sec, block_id, config_json, result_json, create_time, modify_time
                    FROM working_blocks
                """)
                cursor.execute("DROP TABLE working_blocks")
                cursor.execute("ALTER TABLE working_blocks_new RENAME TO working_blocks")
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_id ON working_blocks(id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_name ON working_blocks(project_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON working_blocks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_create_time ON working_blocks(create_time)")
            
            conn.commit()
            conn.close()
    
    def insert(self, working_block: WorkingBlock) -> bool:
        """Insert a new WorkingBlock into the database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                if not working_block.create_time:
                    working_block.create_time = now
                if not working_block.modify_time:
                    working_block.modify_time = now
                
                cursor.execute("""
                    INSERT INTO working_blocks 
                    (id, project_name, method_name, status, retries,
                     prev_ids, output_path, accumulated_duration_sec, block_id, action_index,
                     config_json, result_json, create_time, modify_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    working_block.id,
                    working_block.project_name,
                    working_block.method_name,
                    working_block.status.value,
                    working_block.retries,
                    json.dumps(working_block.prev_ids or []),
                    working_block.output_path,
                    working_block.accumulated_duration_sec,
                    working_block.block_id,
                    working_block.action_index,
                    working_block.config_json,
                    working_block.result_json,
                    working_block.create_time,
                    working_block.modify_time
                ))
                
                conn.commit()
                return True
            except sqlite3.IntegrityError as e:
                print(f"[WorkingBlockDAO] Error inserting working block {working_block.id}: {e}")
                return False
            finally:
                conn.close()
    
    def create_working_block(self, working_block: WorkingBlock) -> bool:
        """Alias for insert() for backward compatibility."""
        return self.insert(working_block)
    
    def get_by_id(self, working_id: str) -> Optional[WorkingBlock]:
        """Get a WorkingBlock by its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT {self.SELECT_FIELDS}
                FROM working_blocks 
                WHERE id = ?
            """, (working_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Parse prev_ids from JSON
            prev_ids = []
            if row[5]:
                try:
                    prev_ids = json.loads(row[5])
                except (json.JSONDecodeError, TypeError):
                    prev_ids = []
            
            return WorkingBlock(
                id=row[0],
                project_name=row[1],
                method_name=row[2],
                status=WorkingBlockStatus(row[3]),
                retries=row[4] or 0,
                prev_ids=prev_ids,
                output_path=row[6],
                accumulated_duration_sec=row[7] or 0.0,
                block_id=row[8],
                action_index=row[9] if len(row) > 9 and row[9] is not None else None,
                config_json=row[10] or "" if len(row) > 10 else "",
                result_json=row[11] or "" if len(row) > 11 else "",
                create_time=row[12] if len(row) > 12 else None,
                modify_time=row[13] if len(row) > 13 else None
            )
        finally:
            conn.close()
    
    def get_working_block(self, working_id: str) -> Optional[WorkingBlock]:
        """Alias for get_by_id() for backward compatibility."""
        return self.get_by_id(working_id)
    
    def get_all(self, project_name: str = None) -> List[WorkingBlock]:
        """Get all WorkingBlocks, optionally filtered by project_name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if project_name:
                cursor.execute(f"""
                    SELECT {self.SELECT_FIELDS}
                    FROM working_blocks 
                    WHERE project_name = ?
                    ORDER BY create_time ASC
                """, (project_name,))
            else:
                cursor.execute(f"""
                    SELECT {self.SELECT_FIELDS}
                    FROM working_blocks 
                    ORDER BY create_time ASC
                """)
            
            rows = cursor.fetchall()
            working_blocks = []
            
            for row in rows:
                # Parse prev_ids from JSON
                prev_ids = []
                if row[5]:
                    try:
                        prev_ids = json.loads(row[5])
                    except (json.JSONDecodeError, TypeError):
                        prev_ids = []
                
                working_blocks.append(WorkingBlock(
                    id=row[0],
                    project_name=row[1],
                    method_name=row[2],
                    status=WorkingBlockStatus(row[3]),
                    retries=row[4] or 0,
                    prev_ids=prev_ids,
                    output_path=row[6],
                    accumulated_duration_sec=row[7] or 0.0,
                    block_id=row[8],
                    action_index=row[9] if len(row) > 9 and row[9] is not None else None,
                    config_json=row[10] or "" if len(row) > 10 else "",
                    result_json=row[11] or "" if len(row) > 11 else "",
                    create_time=row[12] if len(row) > 12 else None,
                    modify_time=row[13] if len(row) > 13 else None
                ))
            
            return working_blocks
        finally:
            conn.close()
    
    def get_all_working_blocks(self, project_id: str = None) -> List[WorkingBlock]:
        """Alias for get_all() for backward compatibility."""
        return self.get_all(project_id)
    
    def update(self, working_block: WorkingBlock) -> bool:
        """Update an existing WorkingBlock."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                working_block.modify_time = now
                
                cursor.execute("""
                    UPDATE working_blocks 
                    SET project_name = ?, method_name = ?, status = ?, retries = ?,
                        prev_ids = ?, output_path = ?, accumulated_duration_sec = ?, block_id = ?, action_index = ?, config_json = ?, result_json = ?, modify_time = ?
                    WHERE id = ?
                """, (
                    working_block.project_name,
                    working_block.method_name,
                    working_block.status.value,
                    working_block.retries,
                    json.dumps(working_block.prev_ids or []),
                    working_block.output_path,
                    working_block.accumulated_duration_sec,
                    working_block.block_id,
                    working_block.action_index,
                    working_block.config_json,
                    working_block.result_json,
                    working_block.modify_time,
                    working_block.id
                ))
                
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"[WorkingBlockDAO] Error updating working block {working_block.id}: {e}")
                return False
            finally:
                conn.close()
    
    def update_working_block(self, working_block: WorkingBlock) -> bool:
        """Alias for update() for backward compatibility."""
        return self.update(working_block)
    
    def delete(self, working_id: str) -> bool:
        """Delete a WorkingBlock by ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM working_blocks WHERE id = ?", (working_id,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"[WorkingBlockDAO] Error deleting working block {working_id}: {e}")
                return False
            finally:
                conn.close()
    
    def delete_working_block(self, working_id: str) -> bool:
        """Alias for delete() for backward compatibility."""
        return self.delete(working_id)
    
    def get_pending(self, project_name: str = None) -> List[WorkingBlock]:
        """Get all pending WorkingBlocks, optionally filtered by project_name."""
        all_blocks = self.get_all(project_name)
        return [wb for wb in all_blocks if wb.status == WorkingBlockStatus.PENDING]
    
    def get_pending_working_blocks(self) -> List[WorkingBlock]:
        """Alias for get_pending() for backward compatibility."""
        return self.get_pending()
    
    def get_completed(self, project_name: str = None) -> List[WorkingBlock]:
        """Get all completed WorkingBlocks (success or error), optionally filtered by project_name."""
        all_blocks = self.get_all(project_name)
        return [wb for wb in all_blocks 
                if wb.status in [WorkingBlockStatus.SUCCESS, WorkingBlockStatus.ERROR]]
    
    def get_completed_working_blocks(self) -> List[WorkingBlock]:
        """Alias for get_completed() for backward compatibility."""
        return self.get_completed()

    def get_by_method_name(self, project_name: str, block_id: str, method_name: str) -> Optional[WorkingBlock]:
        """Return a WorkingBlock for the given project_name + block_id + method_name.
        If multiple blocks match, returns the one with the lowest action_index (first action).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                           SELECT {self.SELECT_FIELDS}
                           FROM working_blocks
                           WHERE project_name = ?
                             AND block_id = ?
                             AND method_name = ?
                           ORDER BY action_index ASC NULLS LAST
                           LIMIT 1
                           """, (project_name, block_id, method_name))

            row = cursor.fetchone()
            if not row:
                return None

            prev_ids = []
            if row[5]:
                try:
                    prev_ids = json.loads(row[5])
                except:
                    prev_ids = []

            return WorkingBlock(
                id=row[0],
                project_name=row[1],
                method_name=row[2],
                status=WorkingBlockStatus(row[3]),
                retries=row[4] or 0,
                prev_ids=prev_ids,
                output_path=row[6],
                accumulated_duration_sec=row[7] or 0.0,
                block_id=row[8],
                action_index=row[9] if len(row) > 9 and row[9] is not None else None,
                config_json=row[10] or "" if len(row) > 10 else "",
                result_json=row[11] or "" if len(row) > 11 else "",
                create_time=row[12] if len(row) > 12 else None,
                modify_time=row[13] if len(row) > 13 else None,
            )
        finally:
            conn.close()
    
    def get_by_action_index(self, project_name: str, block_id: str, action_index: int) -> Optional[WorkingBlock]:
        """Return a WorkingBlock for the given project_name + block_id + action_index."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                           SELECT {self.SELECT_FIELDS}
                           FROM working_blocks
                           WHERE project_name = ?
                             AND block_id = ?
                             AND action_index = ?
                           LIMIT 1
                           """, (project_name, block_id, action_index))

            row = cursor.fetchone()
            if not row:
                return None

            prev_ids = []
            if row[5]:
                try:
                    prev_ids = json.loads(row[5])
                except:
                    prev_ids = []

            return WorkingBlock(
                id=row[0],
                project_name=row[1],
                method_name=row[2],
                status=WorkingBlockStatus(row[3]),
                retries=row[4] or 0,
                prev_ids=prev_ids,
                output_path=row[6],
                accumulated_duration_sec=row[7] or 0.0,
                block_id=row[8],
                action_index=row[9] if len(row) > 9 and row[9] is not None else None,
                config_json=row[10] or "" if len(row) > 10 else "",
                result_json=row[11] or "" if len(row) > 11 else "",
                create_time=row[12] if len(row) > 12 else None,
                modify_time=row[13] if len(row) > 13 else None,
            )
        finally:
            conn.close()
    
    def get_by_block_id(self, project_name: str, block_id: str) -> List[WorkingBlock]:
        """Return all WorkingBlocks for the given project_name + block_id, ordered by action_index."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                           SELECT {self.SELECT_FIELDS}
                           FROM working_blocks
                           WHERE project_name = ?
                             AND block_id = ?
                           ORDER BY action_index ASC NULLS LAST
                           """, (project_name, block_id))

            rows = cursor.fetchall()
            working_blocks = []

            for row in rows:
                prev_ids = []
                if row[5]:
                    try:
                        prev_ids = json.loads(row[5])
                    except:
                        prev_ids = []

                working_blocks.append(WorkingBlock(
                    id=row[0],
                    project_name=row[1],
                    method_name=row[2],
                    status=WorkingBlockStatus(row[3]),
                    retries=row[4] or 0,
                    prev_ids=prev_ids,
                    output_path=row[6],
                    accumulated_duration_sec=row[7] or 0.0,
                    block_id=row[8],
                    action_index=row[9] if len(row) > 9 and row[9] is not None else None,
                    config_json=row[10] or "" if len(row) > 10 else "",
                    result_json=row[11] or "" if len(row) > 11 else "",
                    create_time=row[12] if len(row) > 12 else None,
                    modify_time=row[13] if len(row) > 13 else None,
                ))

            return working_blocks
        finally:
            conn.close()
