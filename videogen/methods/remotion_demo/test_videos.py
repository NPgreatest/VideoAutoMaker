#!/usr/bin/env python3
"""
Final Test Suite for Video Generator
Tests various combinations of templates, durations, and timing parameters
"""

import os
import time
from generate_video import generate_video_direct

def test_video_generation():
    """Comprehensive test suite for video generation"""
    
    print("🎥 Final Video Generator Test Suite")
    print("=" * 50)
    
    # Test cases covering different scenarios
    test_cases = [
        # Desktop Template Tests
        {
            "name": "Desktop - Short Duration (3s)",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "Quick Tech",
            "description": "Fast-paced technology overview.",
            "duration": 3,
            "title_start_time": 900,  # 30% of 3s
        },
        {
            "name": "Desktop - Medium Duration (5s)",
            "template_name": "FilterDesktopSlide", 
            "image_name": "openai.png",
            "title": "AI Revolution",
            "description": "Transforming industries with intelligent automation.",
            "duration": 5,
            "title_start_time": 1500,  # 30% of 5s
        },
        {
            "name": "Desktop - Long Duration (8s)",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png", 
            "title": "Future Technology",
            "description": "Exploring the next generation of technological innovations.",
            "duration": 8,
            "title_start_time": 2400,  # 30% of 8s
        },
        {
            "name": "Desktop - Late Title Start (70%)",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "Late Bloomer",
            "description": "Title appears very late in the video.",
            "duration": 6,
            "title_start_time": 4200,  # 70% of 6s
        },
        {
            "name": "Desktop - Title at Start (0ms)",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "Immediate Start",
            "description": "Title starts immediately.",
            "duration": 5,
            "title_start_time": 0,  # 0% - immediate start
        },
        
        # TikTok Template Tests
        {
            "name": "TikTok - Short Duration (3s)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Quick Byte",
            "description": "Fast tech insights.",
            "duration": 3,
            "title_start_time": 900,  # 30% of 3s
        },
        {
            "name": "TikTok - Medium Duration (6s)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Tech Innovation",
            "description": "Building the future with cutting-edge technology.",
            "duration": 6,
            "title_start_time": 1800,  # 30% of 6s
        },
        {
            "name": "TikTok - Long Duration (10s)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Deep Dive Tech",
            "description": "Comprehensive exploration of advanced technological concepts.",
            "duration": 10,
            "title_start_time": 3000,  # 30% of 10s
        },
        {
            "name": "TikTok - Early Title Start (20%)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Early Bird",
            "description": "Title appears early in the video timeline.",
            "duration": 7,
            "title_start_time": 1400,  # 20% of 7s
        },
        {
            "name": "TikTok - Title at End (90%)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Final Word",
            "description": "Title appears near the end.",
            "duration": 6,
            "title_start_time": 5400,  # 90% - near the end
        }
    ]
    
    # Error test cases
    error_test_cases = [
        {
            "name": "Invalid Template",
            "template_name": "InvalidTemplate",
            "image_name": "openai.png",
            "title": "Test",
            "description": "Test description.",
            "duration": 5,
            "title_start_time": 1500,
        },
        {
            "name": "Duration Too Short (2s)",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "Test",
            "description": "Test description.",
            "duration": 2,  # Below minimum
            "title_start_time": 1000,
        },
        {
            "name": "Duration Too Long (15s)",
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Test",
            "description": "Test description.",
            "duration": 15,  # Above maximum
            "title_start_time": 5000,
        },
        {
            "name": "Title Start Time Too Late",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "Test",
            "description": "Test description.",
            "duration": 5,
            "title_start_time": 6000,  # Beyond duration
        }
    ]
    
    # Run successful test cases
    print("\n✅ Testing Successful Cases:")
    print("-" * 40)
    
    successful_tests = 0
    failed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🎬 Test {i}: {test_case['name']}")
        print(f"   Template: {test_case['template_name']}")
        print(f"   Duration: {test_case['duration']}s")
        print(f"   Title Start: {test_case['title_start_time']}ms")
        
        start_time = time.time()
        
        result = generate_video_direct(
            template_name=test_case["template_name"],
            image_name=test_case["image_name"],
            title=test_case["title"],
            description=test_case["description"],
            duration=test_case["duration"],
            title_start_time=test_case["title_start_time"]
        )
        
        end_time = time.time()
        render_time = end_time - start_time
        
        if result["success"]:
            print(f"   ✅ SUCCESS ({render_time:.1f}s)")
            print(f"   📁 Output: {result['output_path']}")
            successful_tests += 1
        else:
            print(f"   ❌ FAILED: {result['error']}")
            failed_tests += 1
    
    # Run error test cases
    print(f"\n\n❌ Testing Error Cases:")
    print("-" * 40)
    
    error_successful = 0
    error_failed = 0
    
    for i, test_case in enumerate(error_test_cases, 1):
        print(f"\n🚫 Error Test {i}: {test_case['name']}")
        
        result = generate_video_direct(
            template_name=test_case["template_name"],
            image_name=test_case["image_name"],
            title=test_case["title"],
            description=test_case["description"],
            duration=test_case["duration"],
            title_start_time=test_case["title_start_time"]
        )
        
        if not result["success"]:
            print(f"   ✅ CORRECTLY FAILED: {result['error']}")
            error_successful += 1
        else:
            print(f"   ❌ UNEXPECTED SUCCESS: Should have failed!")
            error_failed += 1
    
    # Summary
    print(f"\n\n📊 Test Summary:")
    print("=" * 40)
    print(f"✅ Successful Tests: {successful_tests}/{len(test_cases)}")
    print(f"❌ Failed Tests: {failed_tests}/{len(test_cases)}")
    print(f"✅ Error Tests Passed: {error_successful}/{len(error_test_cases)}")
    print(f"❌ Error Tests Failed: {error_failed}/{len(error_test_cases)}")
    
    total_tests = len(test_cases) + len(error_test_cases)
    total_passed = successful_tests + error_successful
    success_rate = (total_passed / total_tests) * 100
    
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({total_passed}/{total_tests})")
    
    if success_rate == 100:
        print("🎉 All tests passed! The video generator is working perfectly.")
    elif success_rate >= 90:
        print("👍 Most tests passed! The video generator is working well.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

def test_performance():
    """Test rendering performance"""
    print(f"\n\n⚡ Performance Test:")
    print("-" * 30)
    
    test_case = {
        "template_name": "FilterDesktopSlide",
        "image_name": "openai.png",
        "title": "Performance Test",
        "description": "Testing rendering speed.",
        "duration": 5,
        "title_start_time": 1500
    }
    
    start_time = time.time()
    result = generate_video_direct(**test_case)
    end_time = time.time()
    
    if result["success"]:
        render_time = end_time - start_time
        print(f"✅ Performance Test Passed")
        print(f"⏱️  Render Time: {render_time:.1f} seconds")
        print(f"📁 Output: {result['output_path']}")
        
        if render_time < 30:
            print("🚀 Excellent performance!")
        elif render_time < 60:
            print("👍 Good performance!")
        else:
            print("⚠️  Slow performance - consider optimization")
    else:
        print(f"❌ Performance Test Failed: {result['error']}")

def show_project_structure():
    """Show the cleaned up project structure"""
    print(f"\n\n📁 Project Structure:")
    print("-" * 30)
    print("remotion_demo/")
    print("├── remotion_project/")
    print("│   ├── src/")
    print("│   │   ├── FilterDesktopSlide.tsx    # Desktop template (16:9)")
    print("│   │   ├── FilterTikTokSlide.tsx     # TikTok template (9:16)")
    print("│   │   ├── Root.tsx                  # Only 2 compositions")
    print("│   │   └── load-fonts.ts            # Google Fonts")
    print("│   ├── public/assets/openai.png     # Image assets")
    print("│   └── package.json                 # Dependencies")
    print("├── generate_video.py                 # Simplified API")
    print("├── test_videos.py                    # Test suite")
    print("├── demo.py                          # Demo script")
    print("├── requirements.txt                 # Python dependencies")
    print("└── output/                          # Generated videos")

if __name__ == "__main__":
    test_video_generation()
    test_performance()
    show_project_structure()