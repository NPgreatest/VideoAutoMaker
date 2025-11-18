#!/usr/bin/env python3
"""
try_text_video.py - Concise examples of using TextVideoSilicon with the new worker system
Demonstrates the method-integrated worker system for text-to-video generation
Limited to 3 videos to minimize API costs
"""

from __future__ import annotations
import time
from pathlib import Path
from videogen.methods.text_video_silicon import TextVideoSilicon
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.schema.schema import ScriptBlock


def create_test_output_dir():
    """Create the _test_out directory if it doesn't exist"""
    test_dir = Path("./_test_out")
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def wait_for_video_completion(working_id: str, timeout_seconds: int = 300) -> bool:
    """Wait for a video generation task to complete by polling the process_working_block method"""
    dao = WorkingBlockDAO()
    method = TextVideoSilicon()
    start_time = time.time()
    
    print(f"⏳ Waiting for video generation to complete...")
    
    while time.time() - start_time < timeout_seconds:
        working_block = dao.get_working_block(working_id)
        if not working_block:
            print(f"❌ WorkingBlock {working_id} not found")
            return False
        
        print(f"🎬 Checking status for WorkingBlock {working_id}...")
        result = method.process_working_block(working_block)
        
        if result:
            print(f"✅ Video generation completed successfully!")
            return True
        
        # Check if the task failed (not just still processing)
        if working_block.block and working_block.block.video_generation:
            video_gen = working_block.block.video_generation
            if hasattr(video_gen, 'ok'):
                is_ok = video_gen.ok
                error = video_gen.error
            else:
                is_ok = video_gen.get('ok', False)
                error = video_gen.get('error')
            
            if not is_ok and error:
                print(f"❌ Video generation failed: {error}")
                return False
        
        print(f"🔄 Still processing... (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(10)  # Wait 10 seconds before next check
    
    print(f"⏰ Timeout waiting for video generation (>{timeout_seconds}s)")
    return False


def process_working_block_directly(working_id: str) -> bool:
    """Process a WorkingBlock directly using the method (single check)"""
    dao = WorkingBlockDAO()
    method = TextVideoSilicon()
    
    working_block = dao.get_working_block(working_id)
    if not working_block:
        print(f"❌ WorkingBlock {working_id} not found")
        return False
    
    print(f"🎬 Processing WorkingBlock {working_id}...")
    result = method.process_working_block(working_block)
    
    if result:
        print(f"✅ Processing successful!")
        return True
    else:
        print(f"❌ Processing failed!")
        return False


def example_1_basic_video():
    """Example 1: Basic text-to-video generation"""
    print("🎬 Example 1: Basic Text-to-Video")
    print("=" * 40)
    
    method = TextVideoSilicon()
    workdir = create_test_output_dir()
    
    block = ScriptBlock(
        id="ai_future_scene",
        text="生成一个关于人工智能未来的短片。",
        prompt="镜头从宇宙星空慢慢拉近到城市夜景，霓虹灯闪烁，展示热闹的湾区街景。",
        decision="text_video"
    )
    
    result = method.run(
        prompt="镜头从宇宙星空慢慢拉近到城市夜景，霓虹灯闪烁，展示热闹的湾区街景。",
        project="text_to_video_demo",
        target_name="ai_future_scene",
        text="生成一个关于人工智能未来的短片。",
        workdir=workdir,
        duration_ms=10000,
        block=block
    )
    
    if result["ok"]:
        working_id = result["meta"]["working_id"]
        print(f"📤 WorkingBlock created: {working_id}")
        
        success = wait_for_video_completion(working_id)
        if success:
            dao = WorkingBlockDAO()
            updated_block = dao.get_working_block(working_id)
            if updated_block and updated_block.block and updated_block.block.video_generation:
                video_result = updated_block.block.video_generation
                if hasattr(video_result, 'ok') and video_result.ok:
                    print(f"✅ Video created at: {video_result.artifacts[0]}")
                elif isinstance(video_result, dict) and video_result.get('ok', False):
                    print(f"✅ Video created at: {video_result['artifacts'][0]}")
                else:
                    print(f"❌ Video generation failed: {video_result.error if hasattr(video_result, 'error') else video_result.get('error', 'Unknown error')}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_2_multiple_videos():
    """Example 2: Generate 2 additional videos (3 total)"""
    print("🎬 Example 2: Multiple Videos (2 more)")
    print("=" * 40)
    
    method = TextVideoSilicon()
    workdir = create_test_output_dir()
    
    blocks = [
        ScriptBlock(
            id="tech_scene",
            text="科技创新的未来",
            prompt="现代科技实验室，机器人正在工作，全息投影显示数据流",
            decision="text_video"
        ),
        ScriptBlock(
            id="nature_scene",
            text="自然风光",
            prompt="美丽的山景，瀑布从高处流下，阳光透过云层洒向大地",
            decision="text_video"
        )
    ]
    
    for i, block in enumerate(blocks, 1):
        result = method.run(
            prompt=block.prompt,
            project="multi_video_demo",
            target_name=block.id,
            text=block.text,
            workdir=workdir,
            duration_ms=8000,
            block=block
        )
        
        if result["ok"]:
            working_id = result["meta"]["working_id"]
            print(f"📤 Video {i+1} WorkingBlock: {working_id}")
            
            success = wait_for_video_completion(working_id)
            if success:
                dao = WorkingBlockDAO()
                updated_block = dao.get_working_block(working_id)
                if updated_block and updated_block.block and updated_block.block.video_generation:
                    video_result = updated_block.block.video_generation
                    if hasattr(video_result, 'ok') and video_result.ok:
                        print(f"✅ Video {i+1} created at: {video_result.artifacts[0]}")
                    elif isinstance(video_result, dict) and video_result.get('ok', False):
                        print(f"✅ Video {i+1} created at: {video_result['artifacts'][0]}")
                    else:
                        print(f"❌ Video {i+1} failed: {video_result.error if hasattr(video_result, 'error') else video_result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Video {i+1} failed: {result['error']}")
    
    print()


def example_3_prompt_generation():
    """Example 3: Demonstrate prompt generation (no API calls)"""
    print("🎬 Example 3: Prompt Generation")
    print("=" * 40)
    
    method = TextVideoSilicon()
    
    test_texts = [
        "人工智能正在改变世界",
        "未来的科技生活",
        "机器人与人类的合作"
    ]
    
    for text in test_texts:
        prompt = method.generate_prompt(text)
        print(f"📝 '{text}' → '{prompt}'")
    
    print()


def main():
    """Run all examples"""
    print("🎥 TextVideoSilicon Examples (3 Videos Total)")
    print("=" * 50)
    print("Limited to 3 videos to minimize API costs")
    print()
    
    test_dir = create_test_output_dir()
    print(f"📁 Output directory: {test_dir.absolute()}")
    print()
    
    try:
        example_1_basic_video()
        # do not try this example now
        # example_2_multiple_videos()
        # example_3_prompt_generation()
        
        print("🎉 All examples completed!")
        print(f"📁 Check output directory: {test_dir.absolute()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
