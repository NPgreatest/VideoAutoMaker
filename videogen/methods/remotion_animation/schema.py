"""
ActionSchema for remotion_animation method.
"""
from dataclasses import dataclass
from typing import Dict, Any
from videogen.schema.schema_registry import register_schema


@dataclass
class RemotionAnimationSchema:
    """
    Schema for remotion_animation method configuration.
    """
    project_name: str = None
    target_name: str = None
    workdir: str = "."
    template: str = None
    duration_ms: float = None
    data: Dict[str, Any] = None

    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


# Register schema
register_schema("remotion_picture", RemotionAnimationSchema)

