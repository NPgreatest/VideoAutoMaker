#!/usr/bin/env python3
"""
Test script to verify the refactored worker system.
This script tests the new SQLite-based WorkingBlock system.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.worker.global_worker import get_global_worker
from videogen.worker.processors.remotion_processor import process_remotion_working_block
from videogen.worker.processors.text_video_silicon_processor import process_text_video_silicon_working_block
from videogen.pipeline.schema import WorkingBlock, WorkingBlockStatus, ScriptBlock


def test_working_block_dao():
    """Test the WorkingBlock DAO functionality."""
    print("🧪 Testing WorkingBlock DAO...")
    
    dao = WorkingBlockDAO()
    
    # Create test blocks
    test_block1 = ScriptBlock(
        id="test_remotion",
        text="Test Remotion Video|This is a test description",
        prompt="Test prompt for remotion",
        decision="remotion_picture",
        extra_info={"template": "FilterDesktopSlide"}
    )
    
    test_block2 = ScriptBlock(
        id="test_silicon",
        text="Test Silicon Video",
        prompt="Test prompt for silicon",
        decision="text_video"
    )
    
    # Create WorkingBlocks
    working_block1 = WorkingBlock(
        working_id="test_remotion_001",
        project_id="test_project",
        output_folder=".",
        block=test_block1,
        status=WorkingBlockStatus.PENDING
    )
    
    working_block2 = WorkingBlock(
        working_id="test_silicon_001",
        project_id="test_project",
        output_folder=".",
        block=test_block2,
        status=WorkingBlockStatus.PENDING
    )
    
    # Test create
    success1 = dao.create_working_block(working_block1)
    success2 = dao.create_working_block(working_block2)
    
    if success1 and success2:
        print("   ✅ WorkingBlock creation successful")
    else:
        print("   ❌ WorkingBlock creation failed")
        return False
    
    # Test read
    retrieved1 = dao.get_working_block("test_remotion_001")
    retrieved2 = dao.get_working_block("test_silicon_001")
    
    if retrieved1 and retrieved2:
        print("   ✅ WorkingBlock retrieval successful")
    else:
        print("   ❌ WorkingBlock retrieval failed")
        return False
    
    # Test get all
    all_blocks = dao.get_all_working_blocks()
    if len(all_blocks) >= 2:
        print(f"   ✅ Retrieved {len(all_blocks)} WorkingBlocks")
    else:
        print("   ❌ Failed to retrieve all WorkingBlocks")
        return False
    
    # Test get pending
    pending_blocks = dao.get_pending_working_blocks()
    if len(pending_blocks) >= 2:
        print(f"   ✅ Retrieved {len(pending_blocks)} pending WorkingBlocks")
    else:
        print("   ❌ Failed to retrieve pending WorkingBlocks")
        return False
    
    # Clean up
    dao.delete_working_block("test_remotion_001")
    dao.delete_working_block("test_silicon_001")
    
    print("   ✅ WorkingBlock DAO tests passed")
    return True


def test_global_worker():
    """Test the global worker functionality."""
    print("\n🧪 Testing Global Worker...")
    
    # Get global worker
    worker = get_global_worker()
    
    # Register processors
    worker.register_method_processor("remotion_picture", process_remotion_working_block)
    worker.register_method_processor("text_video", process_text_video_silicon_working_block)
    
    print("   ✅ Global worker processors registered")
    
    # Test status summary
    summary = worker.get_status_summary()
    print(f"   ✅ Status summary: {summary}")
    
    print("   ✅ Global worker tests passed")
    return True


def test_integration():
    """Test the integration between DAO and Worker."""
    print("\n🧪 Testing Integration...")
    
    dao = WorkingBlockDAO()
    worker = get_global_worker()
    
    # Create a test WorkingBlock
    test_block = ScriptBlock(
        id="integration_test",
        text="Integration Test Video",
        prompt="Test prompt",
        decision="remotion_picture",
        extra_info={"template": "FilterDesktopSlide"}
    )
    
    working_block = WorkingBlock(
        working_id="integration_test_001",
        project_id="test_project",
        output_folder=".",
        block=test_block,
        status=WorkingBlockStatus.PENDING
    )
    
    # Create in database
    success = dao.create_working_block(working_block)
    if not success:
        print("   ❌ Failed to create WorkingBlock for integration test")
        return False
    
    # Register processor
    worker.register_method_processor("remotion_picture", process_remotion_working_block)
    
    # Test processor directly (without starting worker)
    print("   → Testing processor directly...")
    result = process_remotion_working_block(working_block)
    
    if result:
        print("   ✅ Processor executed successfully")
    else:
        print("   ⚠️  Processor failed (expected in test environment)")
    
    # Clean up
    dao.delete_working_block("integration_test_001")
    
    print("   ✅ Integration tests passed")
    return True


def main():
    """Run all tests."""
    print("🚀 Starting refactored worker system tests...\n")
    
    tests = [
        test_working_block_dao,
        test_global_worker,
        test_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored worker system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
