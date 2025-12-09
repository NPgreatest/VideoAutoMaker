#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wiki2video.core.working_block import WorkingBlockStatus
from wiki2video.schema.action_spec import ActionSpec

from .method import TextImageMethod
from .schema import TextImageConfig


router = APIRouter()


@router.post("/api/text_image")
def create_text_image(config: TextImageConfig):
    """
    FastAPI handler that proxies requests to TextImageMethod.
    """

    method = TextImageMethod()

    try:
        action = ActionSpec(type=method.NAME, config=config.model_dump())
        wb = method.run(action)
        result = method.poll(wb)
    except Exception as exc:  # pragma: no cover - surfaced to HTTP client
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result.status != WorkingBlockStatus.SUCCESS:
        raise HTTPException(status_code=400, detail=result.error or "text_image failed")

    return {
        "status": "success",
        "image_path": result.output_path,
    }


__all__ = ["router"]
