from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .common_schema import BaseModel
from .project_schema import ScriptBlock


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
    status: WorkingBlockStatus = WorkingBlockStatus.PENDING
