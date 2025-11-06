#!/usr/bin/env python3
"""
Videogen CLI - Video Generation Command
Unified video generation pipeline with concatenation.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Import existing pipeline functions
from videogen.pipeline.pipeline import run_pipeline
from videogen.pipeline.concat import concat_pipeline
from videogen.pipeline.utils import read_json, write_json
from videogen.validation.base_validator import validate_project
from videogen.validation.json_validator import JSONValidator

load_dotenv()
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

# ========== Main Function ==========
def generate_video(project_name: str, genAudio: bool = False, genMedia: bool = True):
    """
    Generate complete video from start to finish.
    
    This function implements the complete pipeline:
    1. Check if pipeline is already marked as failed, if so, skip and return
    2. Call the pipeline to generate all resources
    3. Validate the result, if everything is passed, goto concat step
    4. If some job failed, re-run the pipeline again, each block have a retry times,
       if it exceed the max_retry, then return error and stop the entire pipeline,
       mark the pipeline is failed in the json file
    5. Concat the video, if everything is passed, then goto the end
    
    Args:
        project_name: Name of the project
        genAudio: Whether to generate audio
        genMedia: Whether to generate media (videos)
    """
    print("🎬 Starting Complete Video Generation Pipeline")
    print("=" * 60)
    
    input_path = Path(f"./project/{project_name}/{project_name}.json")
    workdir = Path(".")
    
    if not input_path.exists():
        raise SystemExit(f"❌ Project file not found: {input_path}")
    
    # Read JSON file
    raw = read_json(input_path)
    
    # Step 0: Check if pipeline is already marked as failed
    if raw.get("pipeline_failed", False):
        print(f"\n⚠️  Pipeline is already marked as failed for project: {project_name}")
        print("   → Skipping pipeline execution")
        return
    
    # Step 1: Run video generation pipeline
    print("\n📹 STEP 1: Video Generation Pipeline")
    print("-" * 40)
    
    retry_count = 0
    max_retry = MAX_RETRY
    
    while retry_count <= max_retry:
        try:
            # Run pipeline
            run_pipeline(input_path, workdir, genAudio, genMedia)
            
            # Step 2: Validate the result
            print("\n🔍 STEP 2: Validating Results")
            print("-" * 40)
            
            # Register JSON validator
            from videogen.validation.base_validator import get_global_registry
            registry = get_global_registry()
            # Clear any existing validators and register JSON validator
            if registry.get_validator("json_validator") is None:
                registry.register(JSONValidator())
            
            # Validate project
            validation_result = validate_project(project_name, validator_names=["json_validator"])
            
            if not validation_result.get("errors", False):
                print("✅ Validation passed! All resources are generated correctly.")
                break
            else:
                print("❌ Validation failed! Some resources are missing or invalid.")
                print("\n🚨 Validation Errors:")
                for error in validation_result.get("errors", []):
                    print(f"  - {error}")
                
                retry_count += 1
                if retry_count <= max_retry:
                    print(f"\n🔄 Retrying pipeline (attempt {retry_count + 1}/{max_retry + 1})...")
                    time.sleep(60)
                    print("-" * 40)
                else:
                    print(f"\n❌ Maximum retry count ({max_retry}) exceeded!")
                    # Mark pipeline as failed in JSON file
                    raw = read_json(input_path)
                    raw["pipeline_failed"] = True
                    raw["pipeline_failed_reason"] = "Maximum retry count exceeded"
                    raw["pipeline_failed_errors"] = validation_result.get("errors", [])
                    write_json(input_path, raw)
                    print("   → Pipeline marked as failed in JSON file")
                    raise SystemExit("Pipeline failed after maximum retries")
        
        except SystemExit as e:
            # Re-raise SystemExit exceptions
            raise
        except Exception as e:
            retry_count += 1
            print(f"\n❌ Error during pipeline execution: {e}")
            
            if retry_count <= max_retry:
                print(f"\n🔄 Retrying pipeline (attempt {retry_count + 1}/{max_retry + 1})...")
                print("-" * 40)
            else:
                print(f"\n❌ Maximum retry count ({max_retry}) exceeded!")
                # Mark pipeline as failed in JSON file
                raw = read_json(input_path)
                raw["pipeline_failed"] = True
                raw["pipeline_failed_reason"] = f"Pipeline execution failed: {str(e)}"
                write_json(input_path, raw)
                print("   → Pipeline marked as failed in JSON file")
                raise SystemExit(f"Pipeline failed after maximum retries: {e}")
    
    # Step 3: Run concatenation pipeline
    print("\n🔗 STEP 3: Video Concatenation Pipeline")
    print("-" * 40)
    
    try:
        # Use existing concat function
        concat_pipeline(project_name)
        
        print("\n🎉 Complete Video Generation Finished!")
        print("=" * 60)
        print(f"📁 Project directory: project/{project_name}")
        print(f"🎬 Final video (with BGM): project/{project_name}/{project_name}.mp4")
        print(f"🎬 No-BGM video: project/{project_name}/{project_name}_nobgm.mp4")
    except Exception as e:
        print(f"\n❌ Concatenation failed: {e}")
        raise

# ========== Direct Function Call ==========
# This file is now used as a module, not a standalone script
# The main.py handles the execution with hardcoded parameters
