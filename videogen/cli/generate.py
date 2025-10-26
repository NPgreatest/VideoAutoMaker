#!/usr/bin/env python3
"""
Videogen CLI - Video Generation Command
Unified video generation pipeline with concatenation.
"""

from __future__ import annotations

from pathlib import Path

# Import existing pipeline functions
from videogen.pipeline.pipeline import run_pipeline
from videogen.pipeline.concat import concat_pipeline

# ========== Main Function ==========
def generate_video(project_name: str, genDecision: bool = True, genAudio: bool = False, 
                   genPrompt: bool = True, genMedia: bool = True):
    """
    Generate complete video from start to finish.
    
    Args:
        project_name: Name of the project
        genDecision: Whether to generate method decisions
        genAudio: Whether to generate audio
        genPrompt: Whether to generate prompts
        genMedia: Whether to generate media (videos)
    """
    print("🎬 Starting Complete Video Generation Pipeline")
    print("=" * 60)
    
    # Step 1: Run video generation pipeline
    print("\n📹 STEP 1: Video Generation Pipeline")
    print("-" * 40)
    
    input_path = Path(f"./project/{project_name}/{project_name}.json")
    workdir = Path(".")
    
    if not input_path.exists():
        raise SystemExit(f"❌ Project file not found: {input_path}")
    
    # Use existing pipeline function
    run_pipeline(input_path, workdir, genDecision, genAudio, genPrompt, genMedia)
    
    # Step 2: Run concatenation pipeline
    print("\n🔗 STEP 2: Video Concatenation Pipeline")
    print("-" * 40)
    
    # Use existing concat function
    concat_pipeline(project_name)
    
    print("\n🎉 Complete Video Generation Finished!")
    print("=" * 60)
    print(f"📁 Project directory: project/{project_name}")
    print(f"📁 Work directory: project/{project_name}/_work")
    print(f"🎬 Final video: project/{project_name}/_work/{project_name}_burn.mp4")

# ========== Direct Function Call ==========
# This file is now used as a module, not a standalone script
# The main.py handles the execution with hardcoded parameters
