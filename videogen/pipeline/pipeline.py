#!/usr/bin/env python3
from __future__ import annotations

import os.path
import time
import random
from datetime import datetime, timezone
from pathlib import Path

from dacite import from_dict
from dotenv import load_dotenv

from videogen.methods.audio_engine.utils import get_total_audio_duration_ms
from videogen.methods.registry import create_method
import videogen.methods  # This ensures all methods are registered
from videogen.pipeline.schema import ScriptBlock, GenerationResult
from videogen.pipeline.utils import read_json, write_json
from videogen.router.decider import decide_generation_method

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME")


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
        success = wait_for_global_worker_completion(project, timeout_seconds=600)  # 10 minutes timeout
        
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


def run_pipeline(input_path: Path, workdir: Path,genDecision = False, genAudio = False, genPrompt = False, genMedia = False) -> None:
    print(f"🚀 Starting pipeline for: {input_path}")
    raw = read_json(input_path)

    project = raw.get("project", "demo_project")
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]

    for block in blocks:
        print(f"\n🎞️  Processing {block.id} | status={block.status}")

        # --- 决策阶段 ---
        if genDecision and (not block.decision or block.status == "regenerate"):
            method_name = decide_generation_method(block.text, project)
            block.decision = method_name
            print(f"→ Decided method: {method_name}")


        # process Audio part
        totalDuration = None # duration is based from audio
        if block.audio_generation and block.audio_generation.ok:
            audioPath = block.audio_generation.meta['audio_path']
            project_dir = workdir / "project" / project
            fullPath = project_dir / audioPath
            totalDuration = get_total_audio_duration_ms(fullPath)

        if genAudio:
            audioMethod = create_method('silicon_audio')
            result = audioMethod.run(
                    prompt=block.prompt,
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

        if block.status == "done" and (block.video_generation and 'output_path' in block.video_generation.meta and os.path.exists(block.video_generation.meta['output_path'])):
            print("→ Skipped (already done).")
            continue

        # --- Video Part ---
        try:
            method = create_method(block.decision)

            if not block.prompt:
                block.prompt = method.generate_prompt(block.text)

            if genMedia:
                # Retry logic for API rate limits
                max_retries = 3
                base_delay = 2.0
                
                for attempt in range(max_retries):
                    try:
                        result = method.run(
                            prompt=block.prompt,
                            project=project,
                            target_name=block.id,
                            text=block.text,
                            workdir=workdir,
                            duration_ms=totalDuration,
                            block=block,
                        )
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt == max_retries - 1:
                            # Last attempt failed, re-raise the exception
                            raise e
                        
                        # Check if it's a retryable error
                        error_msg = str(e).lower()
                        retryable_keywords = [
                            'rate limit', 'too many requests', '429', 'throttle',
                            'timeout', 'connection', 'network', 'temporary',
                            'service unavailable', '502', '503', '504'
                        ]
                        
                        if any(keyword in error_msg for keyword in retryable_keywords):
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                            print(f"⚠️  Retryable error for {block.id}: {e}")
                            print(f"    Retrying in {delay:.2f}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                        else:
                            # Not a retryable error, re-raise immediately
                            print(f"❌ Non-retryable error for {block.id}: {e}")
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

        except Exception as e:
            block.video_generation = GenerationResult(
                ok=False,
                artifacts=[],
                meta={},
                error=str(e),
            )
            block.status = "error"

        # --- 写回更新 ---
        raw["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for i, b in enumerate(raw["script"]):
            if b["id"] == block.id:
                raw["script"][i] = block.to_dict()
                break

        write_json(input_path, raw)
        print(f"→ Updated JSON ({block.status})")
        
        # Small delay between video generation requests to prevent rate limiting
        if genMedia and block.decision == "text_video":
            delay = random.uniform(1.0, 3.0)
            print(f"⏸️  Waiting {delay:.1f}s before next request to avoid rate limits...")
            time.sleep(delay)

    print("\n✅ Pipeline finished.")
    
    # Wait for all video downloads to complete if any were submitted
    if genMedia:
        _wait_for_video_completion(workdir, project)


if __name__ == "__main__":
    run_pipeline(Path(f"./project/{PROJECT_NAME}/{PROJECT_NAME}.json"), Path("."), True,False   ,True , True)
