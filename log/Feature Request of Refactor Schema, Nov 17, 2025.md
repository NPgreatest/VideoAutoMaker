
# Feature Request of Refactor Schema, Nov 17, 2025
You are an expert software engineer.  
Help me generate the complete schema + pipeline system for my VideoGen project.

---

# 🎯 Project Requirements

I already have:

### ✔ A BaseMethod class  
### ✔ A working global MethodRegistry:

```

videogen/methods/registry.py

```

with:

- `register_method`
- `get_method`
- `create_method`
- `list_methods`

All Method classes will be decorated using:

```

@register_method
class AudioFish(BaseMethod): ...

```

**Method is the execution engine.  
Action = a method invocation with parameters.**

Therefore:

❌ Do NOT generate any BaseActionHandler  
❌ Do NOT duplicate logic inside BaseMethod  
✔ All execution must call `method.run()`  

---

# 🎯 I want you to generate:

A **lightweight Action system**, where:

### 1) ActionSpec (project JSON)
- `id: str`
- `type: str`  ← maps to Method.NAME
- `prev_id: Optional[str]`
- `config: dict`  ← raw config dict

### 2) ActionSchema (per-method typed dataclass)
- Lives under each method folder
- Used to parse ActionSpec.config → strongly typed fields
- Fields must reflect real method needs
- Cursor can design the schema fields based on method responsibility

### 3) SchemaRegistry
- Similar to MethodRegistry
- Map: method_name → schema_class
- Only stores schemas (NOT handlers)

### 4) WorkingBlock (SQLite job)
- runtime job storage
- fields:

```

id: str
action_id: str          # points to ActionSpec.id
type: str               # method name (redundant for lookup)
status: str             # pending / working / done / failed
retries: int
output_path: Optional[str]
prev_working_id: Optional[str]
config_json: str        # dumped ActionSpec.config

```

### 5) Pipeline builder
- Convert `ActionSpec[]` into WorkingBlock rows
- Assign prev_working_id based on linear action list

### 6) Scheduler
- Pick next “pending” working block
- Only runnable if:
  - prev block is done
  - prev output path exists

### 7) Worker
- resolve → schema via SchemaRegistry
- resolve → method instance via MethodRegistry
- call `method.run(...)`
- update WorkingBlock in DB

---

# 🎯 **The primary methods I use (generate folders for each):**

1. `audio_fish`  
2. `text_to_video`  
3. `extract_background_segment`  
4. `overlay_character`  
5. `remotion_animation`

Each method must have:

```

videogen/methods/{method_name}/schema.py
videogen/methods/{method_name}/method.py   # Already exists or stub generated

```

You may infer schema fields based on method purpose.  
Example suggestions:

### audio_fish
- text: str
- voice: str
- speed: float = 1.0

### text_to_video
- prompt: str
- duration: float
- model: str = "wan2.1"

### extract_background_segment
- start_time: float
- end_time: float
- source: str

### overlay_character
- character_image: str
- position: str = "center"
- scale: float = 1.0

### remotion_animation
- animation_type: str
- data: dict

You can redesign fields if needed.

---

# 📁 **Please generate this folder structure:**

```

videogen/
│
├── schema/
│   ├── action_spec.py
│   ├── schema_registry.py
│
├── pipeline/
│   ├── working_block.py
│   ├── builder.py
│   ├── scheduler.py
│   ├── worker.py
│
├── methods/
│   ├── registry.py      # exists – do NOT overwrite
│   │
│   ├── audio_fish/
│   │   ├── schema.py
│   │   └── method.py
│   │
│   ├── text_to_video/
│   │   ├── schema.py
│   │   └── method.py
│   │
│   ├── extract_background_segment/
│   │   ├── schema.py
│   │   └── method.py
│   │
│   ├── overlay_character/
│   │   ├── schema.py
│   │   └── method.py
│   │
│   ├── remotion_animation/
│       ├── schema.py
│       └── method.py
│
└── utils/
├── ffmpeg.py   (stub)
├── file.py     (stub)
└── logger.py   (stub)

```
