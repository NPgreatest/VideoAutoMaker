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
from videogen.pipeline.schema import ScriptBlock, GenerationResult
from videogen.pipeline.utils import read_json, write_json
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


def run_pipeline(input_path: Path, workdir: Path, genAudio = False, genMedia = False) -> None:
    print(f"🚀 Starting pipeline for: {input_path}")
    raw = read_json(input_path)

    # Check if pipeline is already marked as failed
    if raw.get("pipeline_failed", False):
        print(f"⚠️  Pipeline is already marked as failed for this project")
        print(f"   → Skipping pipeline execution")
        return

    project = raw.get("project", "demo_project")
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]

    for block in blocks:
        print(f"\n🎞️  Processing {block.id} | status={block.status}")

        # right now just use text_video
        if not block.decision:
            block.decision = "text_video"

        # process Audio part
        totalDuration = None # duration is based from audio
        if block.audio_generation and block.audio_generation.ok:
            audioPath = block.audio_generation.meta['audio_path']
            project_dir = workdir / "project" / project
            fullPath = project_dir / audioPath
            totalDuration = get_total_audio_duration_ms(fullPath)

        # if we want audio and not finished
        if genAudio and not (block.status == "done" and (
                    block.audio_generation and 'audio_path' in block.audio_generation.meta and os.path.exists(
                block.audio_generation.meta['audio_path']))):

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

        # prompt part
        if not block.prompt:
            block.prompt = method.generate_prompt(block.text)

        if genMedia and not(block.status == "done" and (
                        block.video_generation and 'output_path' in block.video_generation.meta and os.path.exists(
                        block.video_generation.meta['output_path']))):

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
                if genMedia and block.decision == "text_video":
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
                
            # For both methods, mark as "submitted" if successful submission
            if block.video_generation.ok:
                block.status = "submitted"  # Will be updated to "done" by worker
            else:
                block.status = "error"


        # --- 写回更新 ---
        raw["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for i, b in enumerate(raw["script"]):
            if b["id"] == block.id:
                raw["script"][i] = block.to_dict()
                break

        write_json(input_path, raw)
        print(f"→ Updated JSON ({block.status})")
        


    print("\n✅ Pipeline finished.")
    
    # Wait for all video downloads to complete if any were submitted
    if genMedia:
        _wait_for_video_completion(workdir, project)


if __name__ == "__main__":
    run_pipeline(Path(f"./project/{PROJECT_NAME}/{PROJECT_NAME}.json"), Path("."),
                 True, True)
