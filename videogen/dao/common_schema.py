from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
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
