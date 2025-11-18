
# Feature Request: Add background_video support (global background video mode) Nov 15, 2025

## Goal
Enable users to attach a global background video to a project.  
When a background video exists, the pipeline should skip text_to_video generation and instead extract a segment from the background video for each clip.  
The extracted segment duration should match the generated audio length for each ScriptBlock.

---

## Step 1 — Update schema.py
1. Add a new optional field to Project or ScriptBlock (depending on current design):
background_video: Optional[str] = None



2. Ensure that this field is serialized and deserialized in the JSON correctly.

---

## Step 2 — Update gradio_app.py UI
1. Add a new UI component that allows the user to upload or choose a background video.
2. After user confirms, store the path in the project's JSON using the new `background_video` field.
3. Make sure loading an existing project correctly shows the current background video.

---

## Step 3 — Modify the pipeline flow
Inside the main pipeline execution logic (where ScriptBlock → WorkingBlocks are constructed):

1. Detect whether the project has `background_video`.
2. If background_video is set:
- DO NOT create a `text_to_video` step.
- Instead insert a new step: `"extract_background_segment"`.

Example:
tts → extract_background_segment → overlays → compose
   

3. If background_video is NOT set:
   - Keep the existing pipeline:

tts → text_to_video → overlays → compose


---

## Step 4 — Implement extract_background_segment method
Create a new method somewhere in `/pipeline/methods/` (follow existing convention).

Suggested name:

extract_background_segment_method()

 Compute start_time based on cumulative previous clip durations OR 0.0 if you want sequential slices.
 Use ffmpeg to extract:

ffmpeg -i background.mp4 -ss {start} -to {end} -c copy output.mp4

4. Save the output path to ScriptBlock.video_generation or a dedicated field.

---

## Step 5 — Update compose step
Ensure compose step uses:
- extracted background segment
- overlay layers (explain / character)
- audio track

---

## Requirements
- DO NOT break existing pipeline or text_to_video mode.
- The code must be backward compatible.
- The field name should be `background_video` (use consistent naming everywhere).
- The implementation should be easy to extend later (for motion/background registry).

---

## Deliverables
- schema.py updated
- gradio_app UI updated
- pipeline builder modified (conditional sequence)
- new extract_background_segment method implemented
- unit path or json examples updated if necessary


