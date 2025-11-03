from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class BaseModel:
    """Base model with common metadata fields."""
    create_time: str = field(default_factory=now_iso)
    modify_time: str = field(default_factory=now_iso)
    is_delete: bool = False


@dataclass
class GenerationResult:
    """Stores result and metadata for generation steps."""
    ok: bool
    artifacts: List[str]
    meta: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = field(default_factory=now_iso)


@dataclass
class ScriptBlock:
    """
    The data structure representing a script block, stored in JSON file.
    """
    id: str
    text: str
    prompt: str = ""
    context: str = ""
    voice: str = ""
    character: str = ""
    decision: str = "text_video" # or layer_compose
    working_id: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)
    video_generation: Optional[GenerationResult] = None
    audio_generation: Optional[GenerationResult] = None
    status: str = "pending"
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(kw_only=True)
class Project(BaseModel):
    """Project info, stored in MySQL."""
    project_name: str
    project_id: str
    script_path: str = ""


@dataclass
class ProjectJSON(Project):
    """Project info and blocks, stored in JSON file."""
    script: List[ScriptBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class WorkingBlockStatus(Enum):
    """Status enum for WorkingBlock instances."""
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


@dataclass(kw_only=True)
class WorkingBlock(BaseModel):
    """
    Represents a job submitted for execution.
    The result will be written back and polled by the main process.
    """
    working_id: str
    project_id: str
    block: Optional[ScriptBlock] = None
    output_folder: str = ""
    poll_count: int = 0
    quota_cost: int = 0
    status: WorkingBlockStatus = WorkingBlockStatus.PENDING
