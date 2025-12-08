from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional

from wiki2video.schema.action_spec import ActionSpec


def now_iso() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.now(UTC).isoformat(timespec="seconds") + "Z"


@dataclass
class BaseModel:
    """Base model with common metadata fields."""
    create_time: str = field(default_factory=now_iso)
    modify_time: str = field(default_factory=now_iso)
    is_delete: bool = False

@dataclass
class ScriptBlock:
    id: str
    text: str
    actions: List["ActionSpec"]  # 有顺序的 action 链表

class ProjectStatus(Enum):
    """Status enum for Project instances."""
    CREATED = "created"
    AUDIO_GENERATING = "audio_generating"
    AUDIO_READY = "audio_ready"
    VIDEO_GENERATING = "video_generating"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass(kw_only=True)
class ProjectJSON(BaseModel):
    """Project info and blocks, stored in JSON file."""
    project_name: str
    project_id: str
    script: List[ScriptBlock] = field(default_factory=list)
    project_status: ProjectStatus = ProjectStatus.CREATED
    global_context: Optional[str] = None
    show_character_overlay: bool = True
    bgm_path: Optional[str] = None
    background_video: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



