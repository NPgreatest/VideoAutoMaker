#!/usr/bin/env python3
"""
Demo script for the simplified video generator API
"""

from generate_video import generate_video_direct

def demo_api():
    """Demonstrate the simplified API usage"""
    
    print("🎥 Simplified Video Generator Demo")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Desktop AI Video",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "AI Revolution",
            "description": "Transforming industries with intelligent automation.",
            "duration": 5,
            "title_start_time": 1500,
            "sound_effect": "dong_effect.wav"
        },
        {
            "name": "TikTok Tech Video", 
            "template_name": "FilterTikTokSlide",
            "image_name": "openai.png",
            "title": "Tech Innovation",
            "description": "Building the future with cutting-edge technology.",
            "duration": 6,
            "title_start_time": 1800,
            "sound_effect": "dong_effect.wav"
        },
        {
            "name": "Desktop Short Video",
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png", 
            "title": "Future Tech",
            "description": "Revolutionary technology changing the world.",
            "duration": 4,
            "title_start_time": 1200,
            "sound_effect": None
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🎬 Test Case {i}: {test_case['name']}")
        print("-" * 30)
        
        # Generate video
        result = generate_video_direct(
            template_name=test_case["template_name"],
            image_name=test_case["image_name"],
            title=test_case["title"],
            description=test_case["description"],
            duration=test_case["duration"],
            title_start_time=test_case["title_start_time"],
            sound_effect=test_case.get("sound_effect")
        )
        
        if result["success"]:
            print(f"✅ Success!")
            print(f"📁 Output: {result['output_path']}")
            print(f"🎯 Template: {result['template']}")
        else:
            print(f"❌ Failed: {result['error']}")
        
        print()

if __name__ == "__main__":
    demo_api()