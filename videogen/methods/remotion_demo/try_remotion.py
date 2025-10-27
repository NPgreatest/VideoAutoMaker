#!/usr/bin/env python3
"""
try_remotion.py - Examples of using the RemotionMethod
Demonstrates various ways to generate videos using the RemotionMethod class
"""

import os
from pathlib import Path
from method import RemotionMethod


def create_test_output_dir():
    """Create the _test_out directory if it doesn't exist"""
    test_dir = Path("./_test_out")
    test_dir.mkdir(exist_ok=True)
    return test_dir


def example_1_desktop_video():
    """Example 1: Generate a desktop format video with title and description"""
    print("🎬 Example 1: Desktop Video with Title and Description")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="Create a video about AI technology",
        project="ai_demo",
        target_name="ai_revolution_desktop",
        text="AI Revolution | Transforming industries with intelligent automation and machine learning",
        workdir=workdir,
        duration_ms=5000,  # 5 seconds
        block={"template": "FilterDesktopSlide"}
    )
    
    if result["ok"]:
        print(f"✅ Success! Video created at: {result['artifacts'][0]}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"⏱️  Duration: {result['meta']['duration_sec']}s")
        print(f"📝 Title: {result['meta']['title']}")
        print(f"📄 Description: {result['meta']['description']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_2_tiktok_video():
    """Example 2: Generate a TikTok format video with just a title"""
    print("🎬 Example 2: TikTok Video with Title Only")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="Create a short vertical video",
        project="tech_demo",
        target_name="tech_innovation_tiktok",
        text="Tech Innovation",
        workdir=workdir,
        duration_ms=4000,  # 4 seconds
        block={"template": "FilterTikTokSlide"}
    )
    
    if result["ok"]:
        print(f"✅ Success! Video created at: {result['artifacts'][0]}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"⏱️  Duration: {result['meta']['duration_sec']}s")
        print(f"📝 Title: {result['meta']['title']}")
        print(f"📄 Description: {result['meta']['description']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_3_default_template():
    """Example 3: Generate video with default template (no block specified)"""
    print("🎬 Example 3: Default Template (Desktop)")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="Create a video about future technology",
        project="future_demo",
        target_name="future_tech_default",
        text="Future Technology | Building tomorrow's world today",
        workdir=workdir,
        duration_ms=6000,  # 6 seconds
        block=None  # No block specified, should use default
    )
    
    if result["ok"]:
        print(f"✅ Success! Video created at: {result['artifacts'][0]}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"⏱️  Duration: {result['meta']['duration_sec']}s")
        print(f"📝 Title: {result['meta']['title']}")
        print(f"📄 Description: {result['meta']['description']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_4_string_block():
    """Example 4: Generate video with string block parameter"""
    print("🎬 Example 4: String Block Parameter")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="Create a mobile-optimized video",
        project="mobile_demo",
        target_name="mobile_optimized",
        text="Mobile First | Optimized for mobile viewing experience",
        workdir=workdir,
        duration_ms=7000,  # 7 seconds
        block="FilterTikTokSlide"  # String block parameter
    )
    
    if result["ok"]:
        print(f"✅ Success! Video created at: {result['artifacts'][0]}")
        print(f"📊 Template: {result['meta']['template']}")
        print(f"⏱️  Duration: {result['meta']['duration_sec']}s")
        print(f"📝 Title: {result['meta']['title']}")
        print(f"📄 Description: {result['meta']['description']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_5_error_handling():
    """Example 5: Demonstrate error handling with invalid template"""
    print("🎬 Example 5: Error Handling - Invalid Template")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="This should fail",
        project="error_demo",
        target_name="invalid_template",
        text="This will fail",
        workdir=workdir,
        duration_ms=3000,
        block={"template": "InvalidTemplate"}  # Invalid template
    )
    
    if result["ok"]:
        print(f"✅ Unexpected success: {result['artifacts']}")
    else:
        print(f"❌ Expected failure: {result['error']}")
    
    print()


def example_6_empty_text():
    """Example 6: Demonstrate error handling with empty text"""
    print("🎬 Example 6: Error Handling - Empty Text")
    print("=" * 60)
    
    method = RemotionMethod()
    workdir = create_test_output_dir()
    
    result = method.run(
        prompt="This should fail",
        project="error_demo",
        target_name="empty_text",
        text="",  # Empty text
        workdir=workdir,
        duration_ms=3000,
        block={"template": "FilterDesktopSlide"}
    )
    
    if result["ok"]:
        print(f"✅ Unexpected success: {result['artifacts']}")
    else:
        print(f"❌ Expected failure: {result['error']}")
    
    print()


def example_7_prompt_generation():
    """Example 7: Demonstrate prompt generation"""
    print("🎬 Example 7: Prompt Generation")
    print("=" * 60)
    
    method = RemotionMethod()
    
    test_texts = [
        "AI Technology",
        "Machine Learning | Advanced algorithms for data processing",
        "Future Tech | Building tomorrow's innovations"
    ]
    
    for text in test_texts:
        prompt = method.generate_prompt(text)
        print(f"📝 Input: '{text}'")
        print(f"🎯 Generated Prompt: '{prompt}'")
        print()
    
    print()


def main():
    """Run all examples"""
    print("🎥 RemotionMethod Examples")
    print("=" * 80)
    print("This script demonstrates various ways to use the RemotionMethod class")
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
        example_4_string_block()
        example_5_error_handling()
        example_6_empty_text()
        example_7_prompt_generation()
        
        print("🎉 All examples completed!")
        print(f"📁 Check the output directory: {test_dir.absolute()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
