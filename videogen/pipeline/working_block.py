from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class WorkingBlockStatus(Enum):
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class WorkingBlock:
    id: str                     # unique working block uuid
    project_name: str
    method_name: str            # associated method name
    status: WorkingBlockStatus  # pending / success / error
    retries: int = 0
    priority: Optional[int] = None
    last_scheduled_at: Optional[float] = None

    prev_ids: List[str] = None  # List of upstream working block IDs
    output_path: Optional[str] = None
    accumulated_duration_sec: float = 0.0  # Timeline position (seconds)
    block_id: Optional[str] = None  # ScriptBlock.id (e.g., "L1") for path construction
    action_index: Optional[int] = None  # Index of action within the script block

    config_json: str = ""
    result_json: str = ""

    # optional bookkeeping fields
    create_time: Optional[str] = None
    modify_time: Optional[str] = None
    
    def __post_init__(self):
        if self.prev_ids is None:
            self.prev_ids = []
