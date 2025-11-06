#!/usr/bin/env python3
"""
Videogen CLI - Main Entry Point
Debug version with hardcoded choices.
"""

import os

from dotenv import load_dotenv

from videogen.cli import generate_video
from videogen.pipeline.concat import concat_pipeline

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME")


def main():
    """Main CLI entry point - hardcoded for debugging."""
    
    GEN_AUDIO = True
    GEN_MEDIA = True


    print(f"📋 Options: Audio={GEN_AUDIO}, Media={GEN_MEDIA}")

    try:
        generate_video(PROJECT_NAME, GEN_AUDIO, GEN_MEDIA)
    except KeyboardInterrupt:
        print("\n⚠️  Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")


    print("🔗 Running concatenation...")

    try:
        concat_pipeline(PROJECT_NAME)
        print(f"\n🎉 Concatenation completed!")
        print(f"📁 Project directory: project/{PROJECT_NAME}")
        print(f"🎬 Final video (with BGM): project/{PROJECT_NAME}/{PROJECT_NAME}.mp4")
        print(f"🎬 No-BGM video: project/{PROJECT_NAME}/{PROJECT_NAME}_nobgm.mp4")
    except KeyboardInterrupt:
        print("\n⚠️  Concatenation interrupted by user")
    except Exception as e:
        print(f"\n❌ Concatenation failed: {e}")


if __name__ == "__main__":
    main()
