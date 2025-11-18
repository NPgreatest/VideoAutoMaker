# 🔧 Refactor Request — Redesign all file I/O paths using the new hierarchical structure

I want to implement a full architectural refactor for ALL file read/write paths across the entire `videogen` project.

## 🎯 Goal

Adopt the following new file output structure for every WorkingBlock, Method, and pipeline step:

```

{project_root}/blocks/{block_id}/{method_name}/{action_id}/out.*    ← output file
{project_root}/blocks/{block_id}/{method_name}/{action_id}/meta.json
{project_root}/blocks/{block_id}/merged/                            ← (optional merged outputs)

````

Where:

- **block_id = ScriptBlock.id (e.g. "L1")**
- **method_name = BaseMethod.NAME**
- **action_id = ActionSpec.id**
- All intermediate files must be written into that folder.
- Nothing should ever be globally overwritten.
- Each step must leave a trace in its own directory.

## 📌 High-Level Requirements

### 1. Update BaseMethod behavior

Modify BaseMethod so that:

- Every method generates a **deterministic working directory**:

  ```python
  action_dir = (
      project_root
      / "blocks"
      / target_name   # ScriptBlock.id like "L1"
      / method_name   # fish_audio, extract_background_segment, remotion_picture...
      / action_id
  )
````

* All outputs must be placed inside this directory.

* BaseMethod.run() should assign:

  ```python
  working_block.output_path = str(action_dir / "out.<ext>")
  ```

* Each method.poll() must write:

  * output file into this directory
  * meta.json containing:

    * method name
    * action id
    * config
    * timestamps
    * output file name
    * any additional metadata

### 2. Update all Method implementations

Each method under `videogen/methods/*` must:

* Stop writing outputs to shared folders like:

  * `remotion_video/`
  * `audio/`
  * `video/`
  * `workdir/out.mp4`
  * etc.
* Use ONLY the new directory structure.
* Never overwrite previous output from a previous action_id.
* Remove any global or static temporary paths.

Example required rewrite:

```python
output_file = action_dir / "out.mp4"
run ffmpeg or remotion or tts and output into that file
```

### 3. Update Pipeline Builder

When pipeline generates WorkingBlocks, ensure:

* target_name = ScriptBlock.id (e.g., "L1")
* action_id = ActionSpec.id
* method_name = the method.type
* working directory must be derived from project_root

Pipeline builder must not assume any fixed shared folders.

### 4. Update Worker Logic

Worker.poll should:

1. Ensure action_dir exists (create if necessary)
2. After a method finishes:

   * Update working_block.output_path
   * Write meta.json in action_dir
   * Write result_json with ok/error/duration_sec/output_path

Meta file structure example:

```json
{
  "action_id": "737a4bad",
  "method": "remotion_picture",
  "config": {...},
  "output": "out.mp4",
  "timestamp": "2025-11-17T12:00:00Z"
}
```

### 5. Remove all old paths and I/O assumptions

Search the project for old patterns and delete/replace them:

* `remotion_video/*`
* `text_to_video/*`
* `audio_output/*`
* `out_audio.wav`
* `workdir / "remotion" / ...`
* Any code that writes inside the project root directly
* Any code that overwrites files

Replace them with the new standardized directory builder.

### 6. Provide a unified path helper

Create a utility function:

```python
def get_action_output_dir(project_root: Path, block_id: str, method_name: str, action_id: str) -> Path:
    # returns the path {project_root}/blocks/{block_id}/{method_name}/{action_id}/
```

All methods must use this.

### 7. Ensure backward compatibility not required

Break old paths; no need to migrate.

---

## ✔ Implementation details

Cursor should modify:

* `videogen/methods/*`
* `videogen/pipeline/*`
* `videogen/worker/*`
* `videogen/schema/*` (WorkingBlock.output_path usage)
* `videogen/utils/*` if paths assumed
* any file referencing hardcoded output locations

---

## 🔥 Summary

Please apply a full refactor so that:

* Every ActionSpec produces its own isolated output directory
* No two actions ever overwrite each other
* All outputs are grouped by ScriptBlock → Method → ActionID
* Meta files are generated for every action
* All method.run/poll logic uses this new path convention

Make sure all tests and pipeline logic still work under this new output structure.
