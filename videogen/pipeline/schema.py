from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class User:
    """
    User info, stroed in MySQL
    """
    username: str
    email: str
    password: str
    quota: int = 0
    location: str = ""


@dataclass
class GenerationResult:
    ok: bool
    artifacts: List[str]
    meta: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = field(default_factory=now_iso)




@dataclass
class ScriptBlock:
    """
    The data structure representing a script block, storing in the json file.
    """
    id: str
    text: str
    prompt: str = ""
    context: str = ""
    voice: str = ""
    character: str = ""
    decision: str = "subtitle_only"
    working_id : str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)
    video_generation: Optional[GenerationResult] = None
    audio_generation: Optional[GenerationResult] = None
    status: str = "pending"
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkingBlockStatus(Enum):
    """Status enum for WorkingBlock instances"""
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class WorkingBlock:
    """
    This class is a class stored in MySQL, represent a block(job) is submitted for execution.
    The result will store back into the row and the main thread will keep polling the result.
    """
    working_id: str
    project_id: str
    block: [ScriptBlock] = field(default_factory=ScriptBlock)
    output_folder: str = ""
    poll_count: int = 0
    status: Optional[WorkingBlockStatus] = None
    create_time: datetime = field(default_factory=now_iso)
    modify_time: datetime = field(default_factory=now_iso)
    is_delete: bool = False


@dataclass
class Project:
    """
    Project info, stored in MySQL
    """
    project_name: str
    project_id: str
    create_time: str = field(default_factory=now_iso)
    modify_time: str = field(default_factory=now_iso)
    script_path: str = ""
    is_delete: bool = False

@dataclass
class ProjectJSON:
    """
    Project info, stored in Json
    """
    project_name: str
    project_id: str
    script: List[ScriptBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "create_time": self.create_time,
            "modify_time": now_iso(),
            "script": [b.to_dict() for b in self.script],
            "is_delete": self.is_delete,
        }