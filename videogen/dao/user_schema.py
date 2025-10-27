from __future__ import annotations
from dataclasses import dataclass
from .common_schema import BaseModel


@dataclass(kw_only=True)
class User(BaseModel):
    """User info, stored in MySQL."""
    username: str
    email: str
    password: str
    quota: int = 0
    location: str = ""

