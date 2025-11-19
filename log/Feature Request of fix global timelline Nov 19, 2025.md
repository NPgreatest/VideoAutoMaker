You must modify `run_audio_pipeline()` inside `pipeline.py` to perform a **global rebuild of accumulate_duration_sec** after all fish_audio blocks have finished executing.

This rebuild ensures all timeline values are correct even if the user retried only one block.

# =====================================================
# NEW FUNCTION: rebuild_audio_timeline(project_name)
# =====================================================

Add the following function to pipeline.py:

```

def rebuild_audio_timeline(project_name: str):
"""
After audio pipeline finishes (or after a retry), rebuild accumulated timeline
for ALL fish_audio working blocks belonging to this project.

```
RULES:
- Get ALL working blocks where method_name == "fish_audio"
- Sort them by ScriptBlock order: by (block_id, action_index)
- For each block:
    accumulate_duration_sec = previous_accumulate + previous_duration_sec
- All actions within the SAME ScriptBlock share the SAME accumulate_duration_sec
- Save the updated result_json back into WorkingBlockDAO
"""

dao = WorkingBlockDAO()
blocks = dao.get_all(project_name)

# Filter only fish_audio blocks
audio_blocks = [wb for wb in blocks if wb.method_name == "fish_audio"]

# Sort in ScriptBlock order
audio_blocks.sort(key=lambda wb: (wb.block_id, wb.action_index))

current_acc = 0.0
last_block_id = None

for wb in audio_blocks:
    # If new ScriptBlock, use current_acc as its timeline start
    if wb.block_id != last_block_id:
        block_acc = current_acc
        last_block_id = wb.block_id

    # Load existing result_json
    try:
        result = json.loads(wb.result_json or "{}")
    except Exception:
        result = {}

    dur = result.get("duration_sec", 0.0)

    # Update accumulate_duration_sec
    result["accumulate_duration_sec"] = block_acc

    wb.result_json = json.dumps(result)
    dao.update(wb)

    # Advance for next block in sequence
    current_acc = block_acc + dur
```

```

# =====================================================
# INTEGRATION INTO run_audio_pipeline
# =====================================================

At the END of run_audio_pipeline(), AFTER finishing all fish_audio execution:

```

# After running allowed_methods={"fish_audio"}

rebuild_audio_timeline(project_name)

```

This ensures the timeline is always correct after:
- Initial audio pipeline run
- Any retry on any single block
- Cached runs
- Partial re-execution

# =====================================================
# ACCEPTANCE CRITERIA
# =====================================================

- All ScriptBlock-level audio blocks share SAME accumulate_duration_sec
- accumulate_duration_sec is computed strictly from chronological order
- Backwards-compatible with existing DAO entries
- run_audio_pipeline always generates **clean & correct global timeline**
- No fish_audio method must compute timeline by itself
- Video Pipeline can rely on this timeline without rechecking
