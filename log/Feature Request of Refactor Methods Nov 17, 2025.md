You are an expert software engineer.  
Refactor my entire VideoGen pipeline and all method implementations to follow the finalized execution architecture.

==================================================
# 🎯 FINAL EXECUTION MODEL (MUST FOLLOW)
==================================================

We have established the **correct job execution model**:

### ✔ `run(spec: ActionSpec) -> WorkingBlock`
- Creates a new WorkingBlock
- Saves minimal information into SQLite
- DOES NOT execute heavy work
- Stores ActionSpec.config into working_block.config_json
- Assigns working_block.status = PENDING
- Assigns working_block.type = method name
- Returns the WorkingBlock for pipeline builder to persist

### ✔ `poll(wb: WorkingBlock) -> GenerationResult`
- Does ALL actual work
- Do check whether previous WorkingBlock finished(WorkingBlockStatus is success and the output_path exisit)
- May run multiple times (async)
- Or finish in one call (sync)
- Must update:
  - wb.status = SUCCESS or ERROR
  - wb.result_json = JSON of GenerationResult
  - wb.output_path = final output file
- The Worker will write the updated WorkingBlock back to SQLite

### ✔ JSON (project file) never mutates
- ScriptBlock + ActionSpec define the static workflow
- Runtime state is fully stored in SQLite WorkingBlock

### ✔ Worker is the only executor
- Worker loops polling SQLite
- Selects next PENDING job whose dependencies are satisfied
- Calls method.poll()
- Writes updated wb to SQLite

==================================================
# 🎯 TASKS FOR CURSOR
==================================================

You MUST:

# 1) Rewrite ALL method.py under videogen/methods/*
These directories exist:

```

videogen/methods/audio_fish/method.py
videogen/methods/text_to_video/method.py
videogen/methods/extract_background_segment/method.py
videogen/methods/overlay_character/method.py
videogen/methods/remotion_animation/method.py

````

Every method MUST implement:

```python
class XxxMethod(BaseMethod):

    def run(self, spec: ActionSpec) -> WorkingBlock:
        # 1. create WorkingBlock
        # 2. write spec.config → config_json
        # 3. status=PENDING
        # 4. return WorkingBlock

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        # 1. load schema from wb.config_json
        # 2. execute sync or async logic
        # 3. update wb.status/wb.output_path/wb.result_json
        # 4. return GenerationResult
````

Rules:

* Use ActionSchema for parsing config_json
* Use json.loads(wb.config_json)
* Use GenerationResult(ok, output_path, duration_sec, error)
* Do NOT perform real work in run()

==================================================

# 2) Modify videogen/pipeline/pipeline.py

==================================================

Create the following 3 components in this file:

# (A) PipelineBuilder

Converts a ScriptBlock (JSON spec) into WorkingBlock rows stored in SQLite.

Behavior:

* For each ActionSpec in script_block.actions:

  * method = MethodRegistry[action.type]
  * wb = method.run(spec)
  * wb.prev_working_id = previous job id
  * dao.insert(wb)
* JSON stays unchanged

# (B) PipelineScheduler

Selects the next runnable job:

A job is runnable when:

* wb.status == PENDING
* if wb.prev_working_id exists → its previous job must be SUCCESS
* if the previous job has output_path → file must exist

Return that WorkingBlock, or None.

# (C) PipelineWorker

Executes jobs:

```
while True:
    wb = scheduler.next_runnable()
    if wb is None: break

    method = MethodRegistry[wb.type]
    result = method.poll(wb)

    wb.result_json = json.dumps(result.__dict__)
    wb.output_path = result.output_path
    wb.status = SUCCESS or ERROR

    dao.update(wb)
```

Worker must:

* Load schema via SchemaRegistry
* Use MethodRegistry to instantiate method
* Use GenerationResult to store result
* Use SQLite DAO for persistence

==================================================

# 3) Follow proper imports and file structure

==================================================

Ensure correct imports:

* ActionSpec from: `videogen/schema/action_spec.py`
* ScriptBlock from: `videogen/schema/project_schema.py`
* WorkingBlock, WorkingBlockStatus from: `videogen/pipeline/working_block.py`
* MethodRegistry from: `videogen/methods/registry.py`
* SchemaRegistry from: `videogen/schema/schema_registry.py`
* GenerationResult from: `videogen/schema/results.py`

==================================================

# 4) Deliverables

==================================================

Cursor must output:

1. Fully rewritten method.py files:

   * audio_fish
   * text_to_video
   * extract_background_segment
   * overlay_character
   * remotion_animation

2. Fully implemented `videogen/pipeline/pipeline.py` with:

   * PipelineBuilder
   * PipelineScheduler
   * PipelineWorker

3. All code must be consistent with the BaseMethod you already have.

Begin now.
