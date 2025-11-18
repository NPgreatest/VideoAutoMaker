#!/usr/bin/env python3
"""
try_remotion.py - Examples of using the RemotionMethod with the new worker system
Demonstrates how to use the method-integrated worker system for video generation
"""

import time
from pathlib import Path
from videogen.methods.remotion_animation import RemotionMethod
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.schema.schema import ScriptBlock, GenerationResult


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


def example_4_image_integration():
    """Example 4: Demonstrate image integration feature with 3 existing images"""
    print("🎬 Example 4: Image Integration Feature - 3 Videos with Existing Images")
    print("=" * 80)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Define the 3 existing images and their corresponding content
    image_configs = [
        {
            "image_name": "elon.webp",
            "block_id": "elon_musk_video",
            "title": "Elon Musk",
            "description": "Visionary entrepreneur revolutionizing space and technology",
            "template": "FilterDesktopSlide",
            "project": "elon_demo"
        },
        {
            "image_name": "openai_letter.png", 
            "block_id": "openai_letter_video",
            "title": "OpenAI Letter",
            "description": "The future of artificial intelligence and human collaboration",
            "template": "FilterTikTokSlide",
            "project": "openai_demo"
        },
        {
            "image_name": "openai.webp",
            "block_id": "openai_video", 
            "title": "OpenAI",
            "description": "Advancing AI for the benefit of humanity",
            "template": "FilterDesktopSlide",
            "project": "openai_demo"
        }
    ]
    
    # Copy images from example_assets to project folders
    # Get the example_assets directory relative to this file
    example_assets_path = Path(__file__).parent / "example_assets"
    
    for config in image_configs:
        print(f"\n📸 Processing image: {config['image_name']}")
        print("-" * 50)
        
        # Create project directory
        project_dir = workdir / "project" / config["project"]
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy image from example_assets to project folder
        source_image = example_assets_path / config["image_name"]
        dest_image = project_dir / config["image_name"]
        
        if source_image.exists():
            import shutil
            shutil.copy2(str(source_image), str(dest_image))
            print(f"✅ Copied {config['image_name']} to project folder")
        else:
            print(f"❌ Source image not found: {source_image}")
            continue
        
        # Create ScriptBlock with image integration
        block = ScriptBlock(
            id=config["block_id"],
            text=f"{config['title']} | {config['description']}",
            prompt=f"Create a video about {config['title']}",
            decision="remotion_picture",
            extra_info={
                "template": config["template"],
                "single_picture": config["image_name"]
            }
        )
        
        # Use run() method to create WorkingBlock
        result = method.run(
            prompt=f"Create a video about {config['title']}",
            project=config["project"],
            target_name=config["block_id"],
            text=f"{config['title']} | {config['description']}",
            workdir=workdir,
            duration_ms=5000,  # 5 seconds
            block=block
        )
        
        if result["ok"]:
            working_id = result["meta"]["working_id"]
            print(f"📤 WorkingBlock created: {working_id}")
            print(f"📊 Template: {result['meta']['template']}")
            print(f"📸 Custom image: {config['image_name']}")
            print(f"📝 Title: {config['title']}")
            print(f"📄 Description: {config['description']}")
            
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
                        print(f"🖼️  Image used: {video_result.meta.get('props', {}).get('imagePath', 'N/A')}")
                    else:
                        print(f"❌ Video generation failed: {video_result.error}")
            else:
                print(f"❌ Processing failed")
        else:
            print(f"❌ Failed to create WorkingBlock: {result['error']}")
    
    print()


def example_5_video_as_input():
    """Example 5: Render remotion video using an existing video as input"""
    print("🎬 Example 5: Remotion Video with Video Input")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    # Create a test video file (or use existing one)
    project_name = "【户晨风】人到中年没朋友，不是孤独，是清醒"
    project_dir = workdir / "project" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    video_dir = project_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if there's an existing video we can use
    # First, try to find any existing video in the project folder
    test_video_path = None
    existing_videos = list(video_dir.glob("*.mp4"))
    if existing_videos:
        test_video_path = existing_videos[0]
        print(f"📹 Using existing video: {test_video_path.name}")
    else:
        # Try to find a video from other projects
        for other_project_dir in (workdir / "project").glob("*"):
            other_video_dir = other_project_dir / "video"
            if other_video_dir.exists():
                other_videos = list(other_video_dir.glob("*.mp4"))
                if other_videos:
                    test_video_path = other_videos[0]
                    # Copy it to our project
                    import shutil
                    dest_video = video_dir / test_video_path.name
                    shutil.copy2(str(test_video_path), str(dest_video))
                    test_video_path = dest_video
                    print(f"📹 Copied existing video: {test_video_path.name}")
                    break
    
    if not test_video_path or not test_video_path.exists():
        print("⚠️  No existing video found. Creating a dummy video file for testing...")
        # Create a minimal dummy video file (this won't actually work for rendering, but demonstrates the flow)
        test_video_path = video_dir / "test_input_video.mp4"
        test_video_path.write_bytes(b"dummy video content")
        print(f"📹 Created dummy video file: {test_video_path.name}")
        print("⚠️  Note: This is a dummy file. For real rendering, use an actual video file.")
    
    # Prepare image file (if available)
    image_filename = None
    example_assets_path = Path(__file__).parent / "example_assets"
    if example_assets_path.exists():
        available_images = list(example_assets_path.glob("*.png")) + list(example_assets_path.glob("*.webp"))
        if available_images:
            source_image = available_images[0]
            dest_image = project_dir / source_image.name
            import shutil
            shutil.copy2(str(source_image), str(dest_image))
            image_filename = source_image.name
            print(f"📸 Using image: {image_filename}")
    
    # Create ScriptBlock with video_generation already set
    block = ScriptBlock(
        id="video_input_remotion",
        text="AI Technology | Advanced artificial intelligence",
        prompt="Create a remotion video with video background",
        decision="remotion_picture",
        extra_info={
            "template": "FilterTikTokSlide",
            "title": "AI Technology",
            "description": "Advanced artificial intelligence",
            "single_picture": image_filename
        } if image_filename else {
            "template": "FilterTikTokSlide",
            "title": "AI Technology",
            "description": "Advanced artificial intelligence"
        },
        video_generation=GenerationResult(
            ok=True,
            artifacts=[str(test_video_path)],
            meta={
                "output_path": str(test_video_path),
                "duration": 5.0
            },
            error=None
        )
    )
    
    # Create WorkingBlock manually with the block that has video_generation
    dao = WorkingBlockDAO()
    from videogen.schema.schema import WorkingBlock, WorkingBlockStatus
    
    working_block = WorkingBlock(
        working_id=f"video_input_{int(time.time())}",
        project_id=project_name,
        block=block,
        output_folder=str(workdir),
        status=WorkingBlockStatus.PENDING
    )
    
    # Save the WorkingBlock to database
    dao.create_working_block(working_block)
    working_id = working_block.working_id
    
    print(f"📤 WorkingBlock created: {working_id}")
    print(f"📊 Template: {block.extra_info.get('template')}")
    print(f"📝 Title: {block.extra_info.get('title')}")
    print(f"📄 Description: {block.extra_info.get('description')}")
    print(f"📹 Input video: {test_video_path.name}")
    if image_filename:
        print(f"📸 Overlay image: {image_filename}")
    
    # Process the WorkingBlock directly
    print(f"\n🎬 Processing WorkingBlock {working_id}...")
    result = method.process_working_block(working_block)
    
    if result is None:
        print("⏳ Video generation not ready yet (this shouldn't happen in this example)")
    elif result:
        print(f"✅ Remotion rendering successful!")
        
        # Get the updated WorkingBlock to see results
        updated_block = dao.get_working_block(working_id)
        if updated_block and updated_block.block and updated_block.block.remotion_generation:
            remotion_result = updated_block.block.remotion_generation
            if remotion_result.ok:
                print(f"✅ Remotion video created at: {remotion_result.artifacts[0]}")
                print(f"⏱️  Duration: {remotion_result.meta.get('duration_sec', 'N/A')}s")
                print(f"📹 Source video: {remotion_result.meta.get('source_video_path', 'N/A')}")
            else:
                print(f"❌ Remotion generation failed: {remotion_result.error}")
        else:
            print("⚠️  Remotion generation result not found in block")
    else:
        print(f"❌ Remotion rendering failed!")
    
    print()



def main():
    """Run all examples"""
    print("🎥 RemotionMethod Worker System Examples")
    print("=" * 80)
    print("This script demonstrates the new method-integrated worker system")
    print("Including the new image integration feature and video-as-input rendering")
    print("All output videos will be saved to ./_test_out/")
    print()
    
    # Create test output directory
    test_dir = create_test_output_dir()
    print(f"📁 Test output directory: {test_dir.absolute()}")
    print()
    
    # Run examples
    try:
        # example_1_desktop_video()
        # example_2_tiktok_video()
        # example_3_default_template()
        # example_4_image_integration()
        example_5_video_as_input()

        print("🎉 All examples completed!")
        print(f"📁 Check the output directory: {test_dir.absolute()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
