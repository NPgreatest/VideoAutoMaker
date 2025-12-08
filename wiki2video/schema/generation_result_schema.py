from dataclasses import dataclass
from typing import Optional

from wiki2video.core.working_block import WorkingBlockStatus


@dataclass
class GenerationResult:
    status: WorkingBlockStatus
    output_path: Optional[str]
    duration_sec: Optional[float]
    error: Optional[str]
