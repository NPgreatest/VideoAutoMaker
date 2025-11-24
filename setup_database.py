#!/usr/bin/env python3
"""
Database setup script for videogen.
Creates SQLite database for WorkingBlock storage using the latest schema.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus


def setup_database():
    """Initialize the SQLite database for WorkingBlock storage."""
    print("Setting up SQLite database for WorkingBlock storage...")

    db_dir = Path("db")
    db_dir.mkdir(exist_ok=True)

    dao = WorkingBlockDAO()

    print("SQLite database setup completed.")
    print(f"Database location: {dao.db_path}")
    print("Tables created: working_blocks")
    print(
        "Columns: id, project_name, method_name, status, retries, prev_ids, output_path, "
        "accumulated_duration_sec, block_id, action_index, config_json, result_json, create_time, modify_time"
    )

    print("\nTesting database...")

    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    test_block = WorkingBlock(
        id="test_working_id",
        project_name="test_project",
        method_name="remotion_picture",
        status=WorkingBlockStatus.PENDING,
        retries=1,
        prev_ids=["upstream_block_a"],
        output_path="./output/test.mp4",
        accumulated_duration_sec=12.5,
        block_id="script_block_1",
        action_index=0,
        config_json='{"prompt": "Test prompt"}',
        result_json='{"status": "pending"}',
        create_time=now,
        modify_time=now,
    )

    # Ensure a clean slate for the test record
    dao.delete(test_block.id)

    if dao.create_working_block(test_block):
        print("Create operation successful")
    else:
        print("Create operation failed")
        return False

    retrieved_block = dao.get_working_block(test_block.id)
    if retrieved_block and retrieved_block.action_index == test_block.action_index:
        print("Read operation successful")
    else:
        print("Read operation failed")
        return False

    test_block.status = WorkingBlockStatus.SUCCESS
    test_block.result_json = '{"status": "done"}'

    if dao.update_working_block(test_block):
        print("Update operation successful")
    else:
        print("Update operation failed")
        return False

    if dao.delete_working_block(test_block.id):
        print("Delete operation successful")
    else:
        print("Delete operation failed")
        return False

    print("\nAll database tests passed.")
    return True


if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\nDatabase setup completed successfully.")
        sys.exit(0)
    else:
        print("\nDatabase setup failed.")
        sys.exit(1)
