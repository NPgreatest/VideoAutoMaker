#!/usr/bin/env python3
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import backoff
from dacite import from_dict
from dotenv import load_dotenv

from videogen.methods.audio_engine.utils import get_total_audio_duration_ms
from videogen.methods.registry import create_method
from videogen.pipeline.schema import ScriptBlock, GenerationResult, ProjectStatus
from videogen.pipeline.utils import read_json, write_json, set_project_status, get_project_status
from videogen.router.decider import decide_generation_method

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME")

# Backoff retry configuration from .env
BACKOFF_MAX_TRIES = int(os.getenv("BACKOFF_MAX_TRIES", "5"))
BACKOFF_MAX_TIME = int(os.getenv("BACKOFF_MAX_TIME", "120"))


def _wait_for_video_completion(workdir: Path, project: str) -> None:
    """Wait for all video downloads to complete using global worker."""
    try:
        from videogen.worker.global_worker import get_global_worker, start_global_worker, wait_for_global_worker_completion
        
        print("\n⏳ Starting global worker to process video generation...")
        print("   → Worker will process WorkingBlocks from SQLite database...")
        print("   → Worker uses method registry to process tasks automatically...")
        
        # Get the global worker instance
        worker = get_global_worker()
        
        # Check if worker is already running
        if worker.is_running:
            print("   → Worker is already running, will wait for completion...")
        else:
            # Start the global worker
            start_global_worker()
            print("   → Worker started successfully")
        
        # Wait for completion
        print(f"   → Waiting for all tasks in project '{project}' to complete...")
        success = wait_for_global_worker_completion(project, timeout_seconds=6000)  # 100 minutes timeout
        
        if success:
            print("✅ All video generation completed!")
        else:
            print("⚠️  Some video generation tasks may not have completed within timeout")
            print("   → Check worker status or run worker manually to continue processing")
            
    except Exception as e:
        print(f"⚠️  Error in global worker: {e}")
        import traceback
        traceback.print_exc()
        print("   → Check logs for details")


def run_pipeline(input_path: Path, workdir: Path) -> None:
    """
    Run pipeline to generate audio and video resources.
    Automatically checks if resources exist and generates them if missing.
    """
    print(f"🚀 Starting pipeline for: {input_path}")
    raw = read_json(input_path)

    # Check if project is already marked as failed
    project_status = get_project_status(raw)
    if project_status == ProjectStatus.FAILED:
        print(f"⚠️  Project is already marked as failed")
        print(f"   → Skipping pipeline execution")
        return

    project = raw.get("project", "demo_project")
    
    # Set status to GENERATING when starting pipeline
    set_project_status(input_path, ProjectStatus.GENERATING)

    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]

    # Check if project has background_video
    background_video = raw.get("background_video")
    use_background_video = background_video and background_video.strip()

    for block in blocks:
        print(f"\n🎞️  Processing {block.id} | status={block.status}")

        # Determine method based on background_video
        # Force override decision if background_video is set, regardless of existing decision
        if use_background_video:
            block.decision = "extract_background_segment"
            print(f"   → Using background video mode: {background_video}")
        elif not block.decision or block.decision == "":
            # Only set to text_video if decision is empty
            block.decision = "text_video"
            print(f"   → Using text-to-video mode")
        else:
            # Keep existing decision if it's already set and no background_video
            print(f"   → Using existing decision: {block.decision}")
        
        print(f"   → Final decision: {block.decision}")

        # process Audio part
        totalDuration = None # duration is based from audio
        if block.audio_generation and block.audio_generation.ok:
            audioPath = block.audio_generation.meta['audio_path']
            project_dir = workdir / "project" / project
            fullPath = project_dir / audioPath
            totalDuration = get_total_audio_duration_ms(fullPath)

        # Check if audio exists, generate if missing
        audio_exists = (
            block.audio_generation and
            'audio_path' in block.audio_generation.meta and
            os.path.exists(block.audio_generation.meta['audio_path'])
        )
        
        if not audio_exists:

            audio_method = create_method('fish_audio')
            result = audio_method.run(
                    project=project,
                    target_name=block.id,
                    text=block.text,
                    workdir=workdir,
                    block=block,
                )
            block.audio_generation = GenerationResult(
                ok=result.get("ok", False),
                artifacts=result.get("artifacts", []),
                meta=result.get("meta", {}),
                error=result.get("error"),
            )
            if block.audio_generation.ok and 'total_duration' in block.audio_generation.meta:
                totalDuration = block.audio_generation.meta['total_duration']
            else:
                raise Exception(f"⚠️  Audio generation failed or missing total_duration for {block.id}")


        # --- Video Part ---
        method = create_method(block.decision)

        # prompt part (only for text_video, not for extract_background_segment)
        if not block.prompt and block.decision == "text_video":
            block.prompt = method.generate_prompt(block.text)

        # Check if video exists, generate if missing
        video_exists = (
            block.video_generation and
            'output_path' in block.video_generation.meta and
            os.path.exists(block.video_generation.meta['output_path'])
        )
        
        if not video_exists:

            # Retry logic with backoff for API errors
            @backoff.on_exception(
                    backoff.expo,
                    Exception,
                    max_tries=BACKOFF_MAX_TRIES,
                    max_time=BACKOFF_MAX_TIME,
                    jitter=backoff.random_jitter
            )
            def _run_method_with_retry():
                """Internal function that runs the method with retry logic."""
                return method.run(
                    project=project,
                    target_name=block.id,
                    text=block.text,
                    workdir=workdir,
                    duration_ms=totalDuration,
                    block=block,
                )
                
            try:
                result = _run_method_with_retry()
                if block.decision == "text_video":
                    delay = random.uniform(5.0, 10.0)
                    print(f"⏸️  Waiting {delay:.1f}s before next request to avoid rate limits...")
                    time.sleep(delay)
            except Exception as e:
                print(f"❌ Error for {block.id} after all retries: {e}")
                raise e

            block.video_generation = GenerationResult(
                ok=result.get("ok", False),
                artifacts=result.get("artifacts", []),
                meta=result.get("meta", {}),
                error=result.get("error"),
            )
                
            # Mark status based on method type
            if block.video_generation.ok:
                if block.decision == "text_video":
                    block.status = "submitted"  # Will be updated to "done" by worker
                else:
                    # extract_background_segment completes immediately
                    block.status = "done"
            else:
                block.status = "error"

        remotion_exists = (
            block.remotion_generation and
            'output_path' in block.remotion_generation.meta and
            os.path.exists(block.remotion_generation.meta['output_path'])
        )
        # Generate remotion if:
        # 1. Remotion doesn't exist yet
        # 2. Block has extra_info (image/picture information)
        # 3. Video generation is complete (for both text_video and extract_background_segment)
        video_ready = (
            block.video_generation and
            block.video_generation.ok and
            'output_path' in block.video_generation.meta and
            os.path.exists(block.video_generation.meta['output_path'])
        )
        if not remotion_exists and block.extra_info and video_ready:
            print(f"   → Generating remotion video for {block.id} (has extra_info and video ready)")
            remotion_method = create_method("remotion_picture")
            remotion_result = remotion_method.run(
                project=project,
                target_name=block.id,
                text=block.text,
                workdir=workdir,
                duration_ms=totalDuration,
                block=block,
            )
            block.remotion_generation = GenerationResult(
                ok=remotion_result.get("ok", False),
                artifacts=remotion_result.get("artifacts", []),
                meta=remotion_result.get("meta", {}),
                error=remotion_result.get("error"),
            )
        elif block.extra_info and not video_ready:
            print(f"   → Skipping remotion for {block.id} (video not ready yet)")
        elif not block.extra_info:
            print(f"   → Skipping remotion for {block.id} (no extra_info)")


        # --- 写回更新 ---
        raw["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for i, b in enumerate(raw["script"]):
            if b["id"] == block.id:
                raw["script"][i] = block.to_dict()
                break

        write_json(input_path, raw)
        print(f"→ Updated JSON ({block.status})")
        


    print("\n✅ Pipeline finished.")

    _wait_for_video_completion(workdir, project)
    
    # After video generation completes, set status to RENDERING
    set_project_status(input_path, ProjectStatus.RENDERING)


if __name__ == "__main__":
    run_pipeline(Path(f"./project/{PROJECT_NAME}/{PROJECT_NAME}.json"), Path("."))
