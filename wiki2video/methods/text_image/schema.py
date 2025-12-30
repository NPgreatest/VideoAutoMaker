#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TextImageConfig(BaseModel):
    """Configuration payload for the text_image method."""

    prompt: Optional[str] = None
    text: Optional[str] = None
    negative_prompt: Optional[str] = None
    size: str = None
    provider: str = None
    target_name: Optional[str] = None
    project_id: Optional[str] = None
    global_context: Optional[str] = None


__all__ = ["TextImageConfig"]
