You will restructure the entire VideoGen system into a **two-stage pipeline**, using the current architecture, WorkingBlockDAO, ScriptBlock DSL, DAG build logic, and Worker execution model.

The new architecture must introduce:

# =====================================================
# 1. TWO-STAGE PIPELINE (MANDATORY)
# =====================================================

We must split the current monolithic pipeline into:

-------------------------------------------------------
## Stage A — Audio Pipeline (Editable + Reviewable)
-------------------------------------------------------
Runs **only fish_audio**

- Builds the full DAG (same Pipeline.build as today)
- But only executes working blocks where method_name == "fish_audio"
- Allows retry per block
- Allows the Gradio UI to play audio and show status
- User must confirm audio before moving forward

Outputs:
- WorkingBlockDAO entries for fish_audio are SUCCESS with output_path
- Other actions remain PENDING (not executed)
- Project status becomes: `AUDIO_READY`

-------------------------------------------------------
## Stage B — Video Pipeline (Non-editable)
-------------------------------------------------------
Runs **all remaining actions**:
extract_background_segment  
remotion_picture  
remotion_video  
concat  
etc.

- Must reuse the same Pipeline.build result
- Must respect dependencies (prev_ids) built already
- Must execute jobs where method_name != "fish_audio"
- Must generate final video only after audio is locked

When finished:
- Project status becomes `FINISHED`

**Important:** Generating video **requires** that all fish_audio blocks are SUCCESS.


# =====================================================
# 2. PROJECT STATUS MACHINE (NEW)
# =====================================================

Update ProjectStatus enum to include:

- CREATED
- AUDIO_GENERATING
- AUDIO_READY
- VIDEO_GENERATING
- FINISHED
- FAILED

Stage flows:

CREATED → AUDIO_GENERATING → AUDIO_READY → VIDEO_GENERATING → FINISHED  
If errors: FAILED


# =====================================================
# 3. PIPELINE REFACTOR REQUIREMENTS
# =====================================================

Modify pipeline.py to add:

-------------------------------------------------------
### A. run_audio_pipeline(input_path)
-------------------------------------------------------
Steps:

1. read project JSON  
2. set status = AUDIO_GENERATING  
3. parse into ProjectJSON  
4. build DAG using Pipeline.build  
5. execute only wb.method_name == "fish_audio"  
   - Option 1: Worker.run_until_complete(allowed_methods={"fish_audio"})  
   - Option 2: Pipeline.run_audio_only()  
6. update only audio-related blocks  
7. if all audio blocks succeeded → set status = AUDIO_READY  
8. else → set status = FAILED

-------------------------------------------------------
### B. run_video_pipeline(input_path)
-------------------------------------------------------
Steps:

1. read project JSON  
2. assert project_status == AUDIO_READY  
3. set status = VIDEO_GENERATING  
4. build DAG again (same Pipeline.build → this is correct)  
5. execute only wb.method_name != "fish_audio"  
6. at end:  
   - if any ERROR → status = FAILED  
   - else → status = FINISHED


# =====================================================
# 4. WORKER MODIFICATION
# =====================================================
Modify Worker.run_until_complete to accept:

```

def run_until_complete(self, allowed_methods: set[str] | None = None):

```

Logic:
- When retrieving next runnable working block:
  - skip any wb whose method_name is not in allowed_methods (if provided)

Modify Pipeline.get_next_runnable to:

```

def get_next_runnable(self, allowed_methods=None):
for wb in dao.get_pending(...):
if allowed_methods and wb.method_name not in allowed_methods:
continue
if deps satisfied:
return wb

```

This enables partial pipeline execution.


# =====================================================
# 5. GRADIO UI REFACTOR (3 main tabs)
# =====================================================

Modify gradio_app.py to contain:

-------------------------------------------------------
## Tab 1 — Create Project
-------------------------------------------------------
(no change)

-------------------------------------------------------
## Tab 2 — Audio Pipeline
-------------------------------------------------------
UI elements:

- Project selector  
- Button: "Generate Audio" → runs generate_audio(project_name)  
- Table showing all ScriptBlocks with audio status  
- Audio players for each block  
- "Retry Audio" button for each block  
- When audio for all blocks = success → show banner “Audio Ready! Go to Video Pipeline tab.”

Must poll using DAO.

-------------------------------------------------------
## Tab 3 — Video Pipeline
-------------------------------------------------------
UI elements:

- Project selector  
- "Generate Video" button (disabled if audio not ready)  
- Table showing block status for all video actions  
- Preview (optional)  
- Final video output  
- When finished → status = FINISHED

Pipeline flows:

- If user clicks Generate Video before AUDIO_READY → show warning + disable button.


# =====================================================
# 6. DAO REQUIREMENTS
# =====================================================

WorkingBlockDAO stays the same.

Audio pipeline will populate only the fish_audio working blocks.

Video pipeline will populate all remaining action entries.

You must NOT delete existing working blocks for video; they should remain PENDING until Stage B.


# =====================================================
# 7. FILE: videogen/cli/generate.py
# =====================================================

Add:

```

def generate_audio(project_name):
run_audio_pipeline(input_path)

def generate_video(project_name):
run_video_pipeline(input_path)

```

Gradio calls:
- Generate Audio → generate_audio
- Generate Video → generate_video


# =====================================================
# 8. IMPLEMENTATION PRINCIPLES
# =====================================================

- Pipeline.build must NOT change; it must still create full DAG.  
- Only Worker.run_until_complete should decide which blocks get executed.  
- Two-stage is primarily controlled by allowed_methods filtering.  
- Project JSON format should stay identical.  
- Well-structured, production-grade design with clean separation.  
- Do not break existing model classes (ScriptBlock, ActionSpec, WorkingBlock).  
- Keep existing imports and folder structure intact.  
- Code must compile and run.


# =====================================================
# 9. DELIVERABLE FOR THIS TASK
# =====================================================

Cursor should:

1. Update pipeline.py (add two new pipelines + worker filtering)
2. Update worker.py (support allowed_methods)
3. Update ProjectStatus enum
4. Update cli/generate.py (generate_audio / generate_video)
5. Update gradio_app.py → 3 main tabs UI structure
6. Ensure working_block flow correct
7. Ensure status machine correct
8. Ensure minimal regression


# =====================================================
# This is a MAJOR REFACTOR; maintain structure, fix imports automatically.
# =====================================================
Please implement the above changes cleanly and consistently.
