from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class WorkingBlockStatus(Enum):
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"

@dataclass
class WorkingBlock:
    id: str
    project_id: str

    method_name: str
    status: WorkingBlockStatus

    polling_count: int = 0
    error_count: int = 0
    priority: Optional[int] = None

    prev_ids: List[str] = None
    output_path: Optional[str] = None
    accumulated_duration_sec: float = 0.0
    block_id: Optional[str] = None
    action_index: Optional[int] = None

    config_json: str = ""
    result_json: str = ""

    create_time: Optional[float] = None
    last_scheduled_at: Optional[float] = None

    def __post_init__(self):
        if self.prev_ids is None:
            self.prev_ids = []

