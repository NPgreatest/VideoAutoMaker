#!/usr/bin/env python3
"""
Database setup script for videogen.
Creates SQLite database for WorkingBlock storage.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from videogen.dao.working_block_dao import WorkingBlockDAO


def setup_database():
    """Initialize the SQLite database for WorkingBlock storage."""
    print("🔧 Setting up SQLite database for WorkingBlock storage...")
    
    # Create database directory
    db_dir = Path("db")
    db_dir.mkdir(exist_ok=True)
    
    # Initialize the DAO (this will create the database and tables)
    dao = WorkingBlockDAO()
    
    print("✅ SQLite database setup completed!")
    print(f"   → Database location: {dao.db_path}")
    print("   → Tables created: working_blocks")
    
    # Test the database
    print("\n🧪 Testing database...")
    
    # Test basic operations
    from videogen.pipeline.schema import WorkingBlock, WorkingBlockStatus, ScriptBlock
    
    # Create a test working block
    test_block = ScriptBlock(
        id="test_block",
        text="Test video generation",
        prompt="Test prompt",
        decision="remotion_picture"
    )
    
    test_working_block = WorkingBlock(
        working_id="test_working_id",
        project_id="test_project",
        output_folder=".",
        block=test_block,
        status=WorkingBlockStatus.PENDING,
        method_name="remotion_picture"  # Test method_name field
    )
    
    # Test create
    success = dao.create_working_block(test_working_block)
    if success:
        print("   ✅ Create operation successful")
    else:
        print("   ❌ Create operation failed")
        return False
    
    # Test read
    retrieved_block = dao.get_working_block("test_working_id")
    if retrieved_block:
        print("   ✅ Read operation successful")
    else:
        print("   ❌ Read operation failed")
        return False
    
    # Test update
    test_working_block.status = WorkingBlockStatus.SUCCESS
    success = dao.update_working_block(test_working_block)
    if success:
        print("   ✅ Update operation successful")
    else:
        print("   ❌ Update operation failed")
        return False
    
    # Test delete
    success = dao.delete_working_block("test_working_id")
    if success:
        print("   ✅ Delete operation successful")
    else:
        print("   ❌ Delete operation failed")
        return False
    
    print("\n✅ All database tests passed!")
    return True


if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\n🎉 Database setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
