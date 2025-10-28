#!/usr/bin/env python3
"""
try_remotion.py - Examples of using the RemotionMethod with the new worker system
Demonstrates how to use the method-integrated worker system for video generation
"""

import os
import time
from pathlib import Path
from method import RemotionMethod
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.schema import ScriptBlock


def create_test_output_dir():
    """Create the _test_out directory if it doesn't exist"""
    test_dir = Path("./_test_out")
    test_dir.mkdir(exist_ok=True)
    return test_dir


def wait_for_working_block_completion(working_id: str, timeout_seconds: int = 60) -> bool:
    """Wait for a WorkingBlock to complete processing"""
    dao = WorkingBlockDAO()
    start_time = time.time()
    
    print(f"⏳ Waiting for WorkingBlock {working_id} to complete...")
    
    while time.time() - start_time < timeout_seconds:
        working_block = dao.get_working_block(working_id)
        if not working_block:
            print(f"❌ WorkingBlock {working_id} not found")
            return False
        
        if working_block.status.value == "success":
            print(f"✅ WorkingBlock {working_id} completed successfully!")
            return True
        elif working_block.status.value == "error":
            print(f"❌ WorkingBlock {working_id} failed")
            return False
        
        print(f"🔄 Status: {working_block.status.value}, Poll count: {working_block.poll_count}")
        time.sleep(2)
    
    print(f"⏰ Timeout waiting for WorkingBlock {working_id}")
    return False


def process_working_block_directly(working_id: str) -> bool:
    """Process a WorkingBlock directly using the method"""
    dao = WorkingBlockDAO()
    method = RemotionMethod()
    
    working_block = dao.get_working_block(working_id)
    if not working_block:
        print(f"❌ WorkingBlock {working_id} not found")
        return False
    
    print(f"🎬 Processing WorkingBlock {working_id} directly...")
    result = method.process_working_block(working_block)
    
    if result:
        print(f"✅ Direct processing successful!")
        return True
    else:
        print(f"❌ Direct processing failed!")
        return False


def example_1_desktop_video():
    """Example 1: Generate a desktop format video using the new worker system"""
    print("🎬 Example 1: Desktop Video with Worker System")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Create a ScriptBlock for the video
    block = ScriptBlock(
        id="ai_revolution_desktop",
        text="AI Revolution | Transforming industries with intelligent automation and machine learning",
        prompt="Create a video about AI technology",
        decision="remotion_picture",
        extra_info={"template": "FilterDesktopSlide"}
    )
    
    # Use run() method to create WorkingBlock
    result = method.run(
        prompt="Create a video about AI technology",
        project="ai_demo",
        target_name="ai_revolution_desktop",
        text="AI Revolution | Transforming industries with intelligent automation and machine learning",
        workdir=workdir,
        duration_ms=5000,  # 5 seconds
        block=block
    )
    
    if result["ok"]:
        working_id = result["meta"]["working_id"]
        print(f"📤 WorkingBlock created: {working_id}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"📝 Title: AI Revolution")
        print(f"📄 Description: Transforming industries with intelligent automation and machine learning")
        
        # Process the WorkingBlock directly
        success = process_working_block_directly(working_id)
        
        if success:
            # Get the updated WorkingBlock to see results
            dao = WorkingBlockDAO()
            updated_block = dao.get_working_block(working_id)
            if updated_block and updated_block.block and updated_block.block.video_generation:
                video_result = updated_block.block.video_generation
                if video_result.ok:
                    print(f"✅ Video created at: {video_result.artifacts[0]}")
                    print(f"⏱️  Duration: {video_result.meta.get('duration_sec', 'N/A')}s")
                else:
                    print(f"❌ Video generation failed: {video_result.error}")
        else:
            print(f"❌ Processing failed")
    else:
        print(f"❌ Failed to create WorkingBlock: {result['error']}")
    
    print()


def example_2_tiktok_video():
    """Example 2: Generate a TikTok format video using the new worker system"""
    print("🎬 Example 2: TikTok Video with Worker System")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Create a ScriptBlock for the video
    block = ScriptBlock(
        id="tech_innovation_tiktok",
        text="Tech Innovation",
        prompt="Create a short vertical video",
        decision="remotion_picture",
        extra_info={"template": "FilterTikTokSlide"}
    )
    
    # Use run() method to create WorkingBlock
    result = method.run(
        prompt="Create a short vertical video",
        project="tech_demo",
        target_name="tech_innovation_tiktok",
        text="Tech Innovation",
        workdir=workdir,
        duration_ms=4000,  # 4 seconds
        block=block
    )
    
    if result["ok"]:
        working_id = result["meta"]["working_id"]
        print(f"📤 WorkingBlock created: {working_id}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"📝 Title: Tech Innovation")
        
        # Process the WorkingBlock directly
        success = process_working_block_directly(working_id)
        
        if success:
            # Get the updated WorkingBlock to see results
            dao = WorkingBlockDAO()
            updated_block = dao.get_working_block(working_id)
            if updated_block and updated_block.block and updated_block.block.video_generation:
                video_result = updated_block.block.video_generation
                if video_result.ok:
                    print(f"✅ Video created at: {video_result.artifacts[0]}")
                    print(f"⏱️  Duration: {video_result.meta.get('duration_sec', 'N/A')}s")
                else:
                    print(f"❌ Video generation failed: {video_result.error}")
        else:
            print(f"❌ Processing failed")
    else:
        print(f"❌ Failed to create WorkingBlock: {result['error']}")
    
    print()


def example_3_default_template():
    """Example 3: Generate video with default template using the new worker system"""
    print("🎬 Example 3: Default Template with Worker System")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Create a ScriptBlock for the video (no template specified)
    block = ScriptBlock(
        id="future_tech_default",
        text="Future Technology | Building tomorrow's world today",
        prompt="Create a video about future technology",
        decision="remotion_picture",
        extra_info={}  # No template specified, should use default
    )
    
    # Use run() method to create WorkingBlock
    result = method.run(
        prompt="Create a video about future technology",
        project="future_demo",
        target_name="future_tech_default",
        text="Future Technology | Building tomorrow's world today",
        workdir=workdir,
        duration_ms=6000,  # 6 seconds
        block=block
    )
    
    if result["ok"]:
        working_id = result["meta"]["working_id"]
        print(f"📤 WorkingBlock created: {working_id}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"📝 Title: Future Technology")
        print(f"📄 Description: Building tomorrow's world today")
        
        # Process the WorkingBlock directly
        success = process_working_block_directly(working_id)
        
        if success:
            # Get the updated WorkingBlock to see results
            dao = WorkingBlockDAO()
            updated_block = dao.get_working_block(working_id)
            if updated_block and updated_block.block and updated_block.block.video_generation:
                video_result = updated_block.block.video_generation
                if video_result.ok:
                    print(f"✅ Video created at: {video_result.artifacts[0]}")
                    print(f"⏱️  Duration: {video_result.meta.get('duration_sec', 'N/A')}s")
                else:
                    print(f"❌ Video generation failed: {video_result.error}")
        else:
            print(f"❌ Processing failed")
    else:
        print(f"❌ Failed to create WorkingBlock: {result['error']}")
    
    print()


def example_4_error_handling():
    """Example 4: Demonstrate error handling with invalid template"""
    print("🎬 Example 4: Error Handling - Invalid Template")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Create a ScriptBlock with invalid template
    block = ScriptBlock(
        id="invalid_template",
        text="This will fail",
        prompt="This should fail",
        decision="remotion_picture",
        extra_info={"template": "InvalidTemplate"}  # Invalid template
    )
    
    # Use run() method to create WorkingBlock
    result = method.run(
        prompt="This should fail",
        project="error_demo",
        target_name="invalid_template",
        text="This will fail",
        workdir=workdir,
        duration_ms=3000,
        block=block
    )
    
    if result["ok"]:
        print(f"❌ Unexpected success: {result}")
    else:
        print(f"✅ Expected failure: {result['error']}")
    
    print()




def main():
    """Run all examples"""
    print("🎥 RemotionMethod Worker System Examples")
    print("=" * 80)
    print("This script demonstrates the new method-integrated worker system")
    print("All output videos will be saved to ./_test_out/")
    print()
    
    # Create test output directory
    test_dir = create_test_output_dir()
    print(f"📁 Test output directory: {test_dir.absolute()}")
    print()
    
    # Run examples
    try:
        example_1_desktop_video()
        example_2_tiktok_video()
        example_3_default_template()
        example_4_error_handling()
        
        print("🎉 All examples completed!")
        print(f"📁 Check the output directory: {test_dir.absolute()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
