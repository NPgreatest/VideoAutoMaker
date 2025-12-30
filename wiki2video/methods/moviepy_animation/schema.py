"""
ActionSchema for the MoviePy animation method (legacy name: remotion_animation).
"""
from dataclasses import dataclass
from typing import Dict, Any
from wiki2video.schema.schema_registry import register_schema


@dataclass
class MoviepyAnimationSchema:
    """
    Schema for remotion_picture method configuration.
    """
    project_id: str = None
    target_name: str = None
    template: str = None
    duration_ms: float = None
    data: Dict[str, Any] = None

    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


# Register schema
register_schema("moviepy_animation", MoviepyAnimationSchema)
