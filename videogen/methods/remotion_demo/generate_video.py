#!/usr/bin/env python3
"""
Simplified Video Generator API
Direct parameter input without LLM - just template, image, text, and timing
"""

import json
import subprocess
import os
from typing import Dict, Any
import pyttsx3

def generate_video_direct(
    template_name: str,
    image_name: str,
    title: str,
    description: str,
    duration: int,
    title_start_time: int,
    sound_effect: str = None,
    output_filename: str = None
) -> Dict[str, Any]:
    """
    Generate video directly with provided parameters
    
    Args:
        template_name: "FilterDesktopSlide" or "FilterTikTokSlide"
        image_name: Image filename (e.g., "openai.png")
        title: Title text (optional - if empty, title won't render)
        description: Description text (optional - if empty, description won't render)
        duration: Video duration in seconds (3-10)
        title_start_time: When title starts appearing in milliseconds (if None and has title, defaults to 50% of duration)
        sound_effect: Sound effect filename (optional - plays when title animation begins, matches title_start_time)
        output_filename: Optional custom output filename
    
    Returns:
        Dict with success status and output path
    """
    
    # Validate template name
    valid_templates = ["FilterDesktopSlide", "FilterTikTokSlide"]
    if template_name not in valid_templates:
        return {
            "success": False,
            "error": f"Invalid template. Must be one of: {valid_templates}"
        }
    
    # Validate duration
    if not (3 <= duration <= 10):
        return {
            "success": False,
            "error": "Duration must be between 3 and 10 seconds"
        }
    
    # Validate title start time (if provided)
    if title_start_time is not None and not (0 <= title_start_time <= duration * 1000):
        return {
            "success": False,
            "error": f"Title start time must be between 0 and {duration * 1000} milliseconds"
        }
    
    # Generate output filename if not provided
    if not output_filename:
        template_suffix = "desktop" if template_name == "FilterDesktopSlide" else "tiktok"
        output_filename = f"output_{template_suffix}_{title.lower().replace(' ', '_')}.mp4"
    
    # Ensure output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    
    # Create props for Remotion
    props = {
        "template": template_name,
        "title": title,
        "description": description,
        "duration": duration,
        "imagePath": image_name,
        "titleStartTime": title_start_time,
        "soundEffect": sound_effect
    }
    
    # Save props to JSON file
    props_path = os.path.join(output_dir, "props.json")
    with open(props_path, 'w') as f:
        json.dump(props, f, indent=2)
    
    try:
        # Render video using Remotion
        cmd = [
            "npx", "remotion", "render",
            template_name,
            output_path,
            "--props", json.dumps(props)
        ]
        
        print(f"🎬 Rendering {template_name} video...")
        print(f"📊 Props: {json.dumps(props, indent=2)}")
        
        result = subprocess.run(cmd, cwd="remotion_project", capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Video generated successfully!")
            print(f"📁 Output: {output_path}")
            
            return {
                "success": True,
                "output_path": output_path,
                "template": template_name,
                "props": props
            }
        else:
            print(f"❌ Rendering failed:")
            print(f"Error: {result.stderr}")
            return {
                "success": False,
                "error": f"Rendering failed: {result.stderr}"
            }
            
    except Exception as e:
        error_msg = f"Error generating video: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

def generate_speech(text: str, output_path: str) -> bool:
    """Generate speech from text using pyttsx3"""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
        
        # Save to file
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        print(f"🎤 Speech generated: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        return False

def main():
    """Main function for testing the API"""
    print("🎥 Simplified Video Generator API")
    print("=" * 50)
    
    # Example usage
    examples = [
        {
            "template_name": "FilterDesktopSlide",
            "image_name": "openai.png",
            "title": "AI Revolution",
            "description": "Transforming industries with intelligent automation.",
            "duration": 5,
            "title_start_time": 1500,
            "sound_effect": "dong_effect.wav"
        },
        {
            "template_name": "FilterTikTokSlide", 
            "image_name": "openai.png",
            "title": "Tech Innovation",
            "description": "Building the future with cutting-edge technology.",
            "duration": 6,
            "title_start_time": 1800,
            "sound_effect": "dong_effect.wav"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n📝 Example {i}:")
        print(f"   Template: {example['template_name']}")
        print(f"   Image: {example['image_name']}")
        print(f"   Title: {example['title']}")
        print(f"   Description: {example['description']}")
        print(f"   Duration: {example['duration']}s")
        print(f"   Title Start: {example['title_start_time']}ms")
        print(f"   Sound Effect: {example.get('sound_effect', 'None')}")
        
        result = generate_video_direct(**example)
        
        if result["success"]:
            print(f"   ✅ Success: {result['output_path']}")
        else:
            print(f"   ❌ Failed: {result['error']}")

if __name__ == "__main__":
    main()