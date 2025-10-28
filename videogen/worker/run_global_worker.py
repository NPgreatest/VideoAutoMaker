#!/usr/bin/env python3
"""
run_global_worker.py - Entry point to manually start the global worker
This script starts the global worker to process pending WorkingBlocks in the database.
"""

import sys
import time
import signal
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from videogen.worker.global_worker import get_global_worker, start_global_worker, stop_global_worker
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.schema import WorkingBlockStatus


def print_status_summary():
    """Print current status of WorkingBlocks in the database"""
    dao = WorkingBlockDAO()
    
    print("📊 Database Status Summary")
    print("=" * 50)
    
    all_blocks = dao.get_all_working_blocks()
    pending_blocks = dao.get_pending_working_blocks()
    completed_blocks = dao.get_completed_working_blocks()
    
    print(f"📋 Total WorkingBlocks: {len(all_blocks)}")
    print(f"⏳ Pending: {len(pending_blocks)}")
    print(f"✅ Completed: {len(completed_blocks)}")
    
    if pending_blocks:
        print(f"\n📝 Pending Tasks:")
        for block in pending_blocks[:5]:  # Show first 5
            block_info = f"  • {block.working_id} ({block.project_id})"
            if block.block:
                block_info += f" - {block.block.decision}"
            print(block_info)
        
        if len(pending_blocks) > 5:
            print(f"  ... and {len(pending_blocks) - 5} more")
    
    print()


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received signal {signum}, stopping worker...")
    stop_global_worker()
    sys.exit(0)


def main():
    """Main function to start the global worker"""
    print("🚀 Global Worker Entry Point")
    print("=" * 50)
    print("This script will start the global worker to process pending WorkingBlocks")
    print("Press Ctrl+C to stop the worker gracefully")
    print()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show current status
    print_status_summary()
    
    # Get the global worker instance
    worker = get_global_worker()
    
    # Check if worker is already running
    if worker.is_running:
        print("⚠️  Global worker is already running!")
        print("Current status:")
        summary = worker.get_status_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
        return
    
    try:
        # Start the worker
        print("🎬 Starting global worker...")
        worker.start()
        
        # Wait a moment for worker to initialize
        time.sleep(1)
        
        # Monitor progress
        print("👀 Monitoring worker progress...")
        print("Press Ctrl+C to stop")
        print()
        
        last_pending_count = -1
        start_time = time.time()
        
        while worker.is_running:
            # Get current status
            summary = worker.get_status_summary()
            pending_count = summary["pending"]
            
            # Only print when count changes
            if pending_count != last_pending_count:
                elapsed = int(time.time() - start_time)
                print(f"⏱️  [{elapsed:03d}s] Pending: {pending_count}, Completed: {summary['success']}, Errors: {summary['error']}")
                last_pending_count = pending_count
            
            # If no pending tasks, wait a bit more then exit
            if pending_count == 0:
                print("✅ All tasks completed! Worker will stop automatically.")
                time.sleep(2)
                break
            
            time.sleep(5)  # Check every 5 seconds
        
        # Final status
        print("\n📊 Final Status:")
        final_summary = worker.get_status_summary()
        for key, value in final_summary.items():
            print(f"  {key}: {value}")
        
        print("\n🎉 Global worker finished!")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Ensure worker is stopped
        if worker.is_running:
            print("🛑 Stopping worker...")
            worker.stop()


if __name__ == "__main__":
    main()
