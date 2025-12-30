"""
ActionSchema for text_audio method.
"""
from dataclasses import dataclass
from typing import Optional
from wiki2video.schema.schema_registry import register_schema


@dataclass
class TextAudioSchema:
    """
    Schema for text_audio method configuration.
    
    Attributes:
        text: Text to convert to speech
        target_name: Target audio file name
        project_id: Project id (optional, will be set by PipelineBuilder)
        global_context: Global theme/context for the video
        speed: Speech speed multiplier (default: 1.2)
    """
    text: str
    target_name: str
    project_id: Optional[str] = None  # Will be set by PipelineBuilder
    global_context: Optional[str] = None
    speed: float = 1.2


# Register schema
register_schema("text_audio", TextAudioSchema)
