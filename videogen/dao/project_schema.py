from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from .common_schema import BaseModel, GenerationResult


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
    decision: str = "subtitle_only"
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
