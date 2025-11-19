#!/usr/bin/env python3
"""
Videogen CLI - Main Entry Point
Debug version with hardcoded choices.
"""

import os

from dotenv import load_dotenv

from videogen.cli import generate_audio, generate_video

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME")


def main():
    """Main CLI entry point - hardcoded for debugging."""
    
    GEN_AUDIO = True
    GEN_MEDIA = True

    print(f"📋 Options: Audio={GEN_AUDIO}, Media={GEN_MEDIA}")

    try:
        if GEN_AUDIO:
            generate_audio(PROJECT_NAME)
        if GEN_MEDIA:
            generate_video(PROJECT_NAME)
    except KeyboardInterrupt:
        print("\n⚠️  Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")


if __name__ == "__main__":
    main()
