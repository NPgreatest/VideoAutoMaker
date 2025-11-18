In /remotion_animation/remotion_project/src/ add a new template called OverlapCharacter, it accept image path and the resize ratio, position, appear: bool as param,
use tsx(remotion) method create animation like @add_picture.py if appear is true. If appear is true, make a slide animation from the left.



# 🔧 Refactor Request — Move from `prev_id` (single chain) to `prev_ids` (multi-upstream DAG-like dependency)

I want to upgrade the core architecture of my `videogen` pipeline.

## 🎯 Goal

Transform the execution dependency model from:

```

WorkingBlock.prev_id: str | None  # single chain

```

into:

```

WorkingBlock.prev_ids: list[str]  # multiple upstream dependencies

````

This allows any WorkingBlock to depend on multiple upstream blocks (e.g., audio accumulation + video segment), enabling more accurate timeline-based video editing and cleaner dependency resolution.

This is NOT a full DAG system.  
This is a **linear script pipeline + multi-upstream WorkingBlock dependency**.

## 📌 High-Level Requirements

### 1. Update schema

#### WorkingBlock
Replace:
```python
prev_working_id: Optional[str]
````

with:

```python
prev_ids: List[str]  # stored as JSON in SQLite
```

Remove `prev_working_id` completely across the project.

Add / keep:

```python
accumulated_duration_sec: float
```

### 2. Update SQLite schema and DAO

Modify `working_blocks` table:

* Add `prev_ids TEXT` (JSON string)
* When reading, decode JSON to Python `List[str]`
* When writing, encode via `json.dumps(prev_ids)`
* Remove all fields related to `prev_working_id`
* Update create/update/get DAO functions to handle prev_ids correctly

### 3. Update ActionSpec (static DSL)

Replace ActionSpec.prev_id → prev_ids:

```python
@dataclass
class ActionSpec:
    id: str
    type: str
    prev_ids: List[str]
    config: Dict[str, Any]
```

Everywhere referencing prev_id must be updated.

### 4. Update pipeline builder

Where previously pipeline created dependencies like:

```python
action.prev_id = previous_action.id
```

now become:

```python
action.prev_ids = [previous_action.id]
```

If an action has multiple upstream dependencies (e.g., cutter method depending on all previous audio blocks), the pipeline builder should set:

```python
action.prev_ids = [list of action_ids]
```

### 5. Update method.run()

When creating WorkingBlock, replace:

```python
prev_working_id = ...
```

with:

```python
prev_ids = list_of_upstream_working_blocks
```

config_json remains the same.

### 6. Update Worker Logic

Worker may only execute a WorkingBlock if:

```
all(prev_block.status == SUCCESS)
```

Pseudo-code:

```python
def is_ready(wb):
    for pid in wb.prev_ids:
        prev = dao.get(pid)
        if not prev or prev.status != SUCCESS:
            return False
    return True
```

### 7. Accumulated Timeline Logic

When executing WorkingBlock:

```python
if wb.prev_ids:
    wb.accumulated_duration_sec = max(
        dao.get(pid).accumulated_duration_sec
        for pid in wb.prev_ids
    )
else:
    wb.accumulated_duration_sec = 0.0
```

After execution:

```python
if result.duration_sec:
    wb.accumulated_duration_sec += result.duration_sec
```

Store this in SQLite.

### 8. Update all method.poll() implementations

Where methods previously relied on `prev_working_id`, they must switch to aggregating dependencies via prev_ids.

### 9. Backward Compatibility

You may safely remove all leftover references to:

* prev_working_id
* block.prev_id
* any variable named "previous"
* any DB field related to prev_working_id

No migration needed—this is a clean breaking update.

---

## ✔ Output Requirements

Cursor should:

1. Update all relevant files:

   * `videogen/schema/*`
   * `videogen/dao/working_block_dao.py`
   * `videogen/pipeline/*`
   * `videogen/methods/*`
   * `worker.py` or equivalent poll loop
   * `setup_database.py`
   * Any other files referencing prev_id or previous jobs

2. Fully ensure WorkingBlock.prev_ids is used everywhere.

3. Ensure the whole project runs under the new prev_ids architecture.

4. Maintain existing naming conventions and structure.

---

## 🚨 Notes

* Do NOT convert to a full DAG scheduler.
  Keep pipeline building linear, but allow multi-upstream runtime dependencies.
* JSON DSL (ProjectJSON + ScriptBlock + ActionSpec) must remain static and free of runtime metadata.
* WorkingBlock continues to be the ONLY runtime state and the only thing saved in SQLite.

---

## 🔥 Final Action

Perform the entire refactor from `prev_id` to `prev_ids` across the entire repo, updating all logic, schemas, DAO, pipeline builder, and worker logic accordingly.

