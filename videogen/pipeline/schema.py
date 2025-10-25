from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class GenerationResult:
    ok: bool
    artifacts: List[str]
    meta: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = field(default_factory=now_iso)


@dataclass
class Decision:
    method: str
    confidence: float = 1.0
    decided_by: str = "llm"


@dataclass
class ScriptBlock:
    id: str
    text: str
    prompt: str = ""
    context: str = ""
    voice: str = ""
    character: str = ""
    decision: Optional[Decision] = None
    generation: Optional[GenerationResult] = None
    audioGeneration: Optional[GenerationResult] = None
    status: str = "pending"
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        # asdict 会递归转换所有 dataclass 子字段
        return asdict(self)



@dataclass
class ProjectJSON:
    project: str
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    script: List[ScriptBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "created_at": self.created_at,
            "updated_at": now_iso(),
            "script": [b.to_dict() for b in self.script],
        }
