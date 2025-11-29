#!/usr/bin/env python3
"""
Database setup script for videogen.
Creates SQLite database for WorkingBlock storage using the latest schema.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus


REQUIRED_COLUMNS = [
    "id",
    "project_name",
    "method_name",
    "status",
    "retries",
    "prev_ids",
    "output_path",
    "accumulated_duration_sec",
    "block_id",
    "action_index",
    "config_json",
    "result_json",
    "priority",
    "last_scheduled_at",
    "create_time",
    "modify_time"
]


def setup_database():
    print("Initializing SQLite database for WorkingBlock storage...\n")

    # ensure db directory exists
    db_dir = Path("db")
    db_dir.mkdir(exist_ok=True)

    dao = WorkingBlockDAO()
    print(f"Database file: {dao.db_path}")

    # ---------------------------------------------------------
    # Validate schema (ensure all required columns exist)
    # ---------------------------------------------------------
    import sqlite3
    conn = sqlite3.connect(dao.db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(working_blocks)")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()

    print("\nChecking schema...")
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]

    if missing:
        print(f"⚠️  WARNING: Missing columns detected: {missing}")
        print("DAO will auto-migrate these fields on next startup.")
    else:
        print("Schema validation OK — all required columns present.")

    print("\nRunning CRUD tests...")

    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    test_block = WorkingBlock(
        id="test_working_id",
        project_name="test_project",
        method_name="remotion_picture",
        status=WorkingBlockStatus.PENDING,
        retries=0,
        prev_ids=["upstream_block"],
        output_path="./output/test.mp4",
        accumulated_duration_sec=1.5,
        block_id="L1",
        action_index=0,
        config_json='{"prompt": "hello"}',
        result_json='{"status": "pending"}',

        # 🚀 new scheduling fields
        priority=5,
        last_scheduled_at=123456.0,

        create_time=now,
        modify_time=now,
    )

    # clean before test
    dao.delete(test_block.id)

    # CREATE
    if dao.insert(test_block):
        print("CREATE OK")
    else:
        print("❌ CREATE FAILED")
        return False

    # READ
    rb = dao.get_by_id(test_block.id)
    if rb and rb.priority == 5:
        print("READ OK")
    else:
        print("❌ READ FAILED")
        return False

    # UPDATE
    test_block.status = WorkingBlockStatus.SUCCESS
    test_block.result_json = '{"status":"done"}'
    test_block.priority = 1

    if dao.update(test_block):
        print("UPDATE OK")
    else:
        print("❌ UPDATE FAILED")
        return False

    # DELETE
    if dao.delete(test_block.id):
        print("DELETE OK")
    else:
        print("❌ DELETE FAILED")
        return False

    print("\nAll CRUD tests passed successfully!")
    return True


if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\n🎉 Database setup completed successfully.")
        sys.exit(0)
    else:
        print("\n❌ Database setup encountered errors.")
        sys.exit(1)
