"""
SQLite DAO for WorkingBlock storage and management.
Replaces the CSV-based storage with a proper SQLite database.
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from videogen.pipeline.schema import WorkingBlock, WorkingBlockStatus, ScriptBlock


class WorkingBlockDAO:
    """SQLite DAO for WorkingBlock management."""
    
    _lock = threading.Lock()
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path("db/working_blocks.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create working_blocks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS working_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    working_id TEXT NOT NULL UNIQUE,
                    project_id TEXT NOT NULL,
                    output_folder TEXT DEFAULT '',
                    poll_count INTEGER DEFAULT 0,
                    quota_cost INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    create_time TEXT NOT NULL,
                    modify_time TEXT NOT NULL,
                    is_delete BOOLEAN DEFAULT FALSE,
                    block_data TEXT,  -- JSON string of ScriptBlock
                    error_message TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_id ON working_blocks(working_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_id ON working_blocks(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON working_blocks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_create_time ON working_blocks(create_time)")
            
            conn.commit()
            conn.close()
    
    def create_working_block(self, working_block: WorkingBlock) -> bool:
        """Create a new WorkingBlock in the database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Serialize block data to JSON
                block_data_json = json.dumps(working_block.block.to_dict()) if working_block.block else None
                
                cursor.execute("""
                    INSERT INTO working_blocks 
                    (working_id, project_id, output_folder, poll_count, quota_cost, 
                     status, create_time, modify_time, is_delete, block_data, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    working_block.working_id,
                    working_block.project_id,
                    working_block.output_folder,
                    working_block.poll_count,
                    working_block.quota_cost,
                    working_block.status.value,
                    working_block.create_time,
                    working_block.modify_time,
                    working_block.is_delete,
                    block_data_json,
                    None
                ))
                
                conn.commit()
                return True
            except sqlite3.IntegrityError as e:
                print(f"[WorkingBlockDAO] Error creating working block {working_block.working_id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_working_block(self, working_id: str) -> Optional[WorkingBlock]:
        """Get a WorkingBlock by its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT working_id, project_id, output_folder, poll_count, quota_cost,
                       status, create_time, modify_time, is_delete, block_data, error_message
                FROM working_blocks 
                WHERE working_id = ? AND is_delete = FALSE
            """, (working_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Deserialize block data
            block_data = None
            if row[9]:  # block_data
                try:
                    block_dict = json.loads(row[9])
                    block_data = ScriptBlock(**block_dict)
                except Exception as e:
                    print(f"[WorkingBlockDAO] Error deserializing block data: {e}")
            
            return WorkingBlock(
                working_id=row[0],
                project_id=row[1],
                output_folder=row[2],
                poll_count=row[3],
                quota_cost=row[4],
                status=WorkingBlockStatus(row[5]),
                create_time=row[6],
                modify_time=row[7],
                is_delete=bool(row[8]),
                block=block_data
            )
        finally:
            conn.close()
    
    def get_all_working_blocks(self, project_id: str = None) -> List[WorkingBlock]:
        """Get all WorkingBlocks, optionally filtered by project_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if project_id:
                cursor.execute("""
                    SELECT working_id, project_id, output_folder, poll_count, quota_cost,
                           status, create_time, modify_time, is_delete, block_data, error_message
                    FROM working_blocks 
                    WHERE project_id = ? AND is_delete = FALSE
                    ORDER BY create_time ASC
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT working_id, project_id, output_folder, poll_count, quota_cost,
                           status, create_time, modify_time, is_delete, block_data, error_message
                    FROM working_blocks 
                    WHERE is_delete = FALSE
                    ORDER BY create_time ASC
                """)
            
            rows = cursor.fetchall()
            working_blocks = []
            
            for row in rows:
                # Deserialize block data
                block_data = None
                if row[9]:  # block_data
                    try:
                        block_dict = json.loads(row[9])
                        block_data = ScriptBlock(**block_dict)
                    except Exception as e:
                        print(f"[WorkingBlockDAO] Error deserializing block data: {e}")
                
                working_blocks.append(WorkingBlock(
                    working_id=row[0],
                    project_id=row[1],
                    output_folder=row[2],
                    poll_count=row[3],
                    quota_cost=row[4],
                    status=WorkingBlockStatus(row[5]),
                    create_time=row[6],
                    modify_time=row[7],
                    is_delete=bool(row[8]),
                    block=block_data
                ))
            
            return working_blocks
        finally:
            conn.close()
    
    def update_working_block(self, working_block: WorkingBlock) -> bool:
        """Update an existing WorkingBlock."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Serialize block data to JSON
                block_data_json = json.dumps(working_block.block.to_dict()) if working_block.block else None
                
                cursor.execute("""
                    UPDATE working_blocks 
                    SET project_id = ?, output_folder = ?, poll_count = ?, quota_cost = ?,
                        status = ?, modify_time = ?, is_delete = ?, block_data = ?, error_message = ?
                    WHERE working_id = ?
                """, (
                    working_block.project_id,
                    working_block.output_folder,
                    working_block.poll_count,
                    working_block.quota_cost,
                    working_block.status.value,
                    working_block.modify_time,
                    working_block.is_delete,
                    block_data_json,
                    None,  # error_message - could be added to WorkingBlock schema if needed
                    working_block.working_id
                ))
                
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"[WorkingBlockDAO] Error updating working block {working_block.working_id}: {e}")
                return False
            finally:
                conn.close()
    
    def delete_working_block(self, working_id: str) -> bool:
        """Soft delete a WorkingBlock by setting is_delete = True."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE working_blocks 
                    SET is_delete = TRUE, modify_time = ?
                    WHERE working_id = ?
                """, (datetime.utcnow().isoformat() + "Z", working_id))
                
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"[WorkingBlockDAO] Error deleting working block {working_id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_pending_working_blocks(self) -> List[WorkingBlock]:
        """Get all pending WorkingBlocks."""
        return [wb for wb in self.get_all_working_blocks() 
                if wb.status == WorkingBlockStatus.PENDING]
    
    def get_completed_working_blocks(self) -> List[WorkingBlock]:
        """Get all completed WorkingBlocks (success or error)."""
        return [wb for wb in self.get_all_working_blocks() 
                if wb.status in [WorkingBlockStatus.SUCCESS, WorkingBlockStatus.ERROR]]
    
    def cleanup_old_blocks(self, days_old: int = 7) -> int:
        """Clean up old completed blocks (hard delete)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cutoff_date = datetime.utcnow().isoformat() + "Z"
                # This is a simplified cleanup - in production you'd want proper date arithmetic
                cursor.execute("""
                    DELETE FROM working_blocks 
                    WHERE status IN ('success', 'error') 
                    AND create_time < datetime('now', '-{} days')
                """.format(days_old))
                
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
            except Exception as e:
                print(f"[WorkingBlockDAO] Error cleaning up old blocks: {e}")
                return 0
            finally:
                conn.close()
