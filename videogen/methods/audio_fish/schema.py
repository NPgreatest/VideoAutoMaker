"""
ActionSchema for audio_fish method.
"""
from dataclasses import dataclass
from typing import Optional
from videogen.schema.schema_registry import register_schema


@dataclass
class AudioFishSchema:
    """
    Schema for audio_fish method configuration.
    
    Attributes:
        text: Text to convert to speech
        target_name: Target audio file name
        project_name: Project name (optional, will be set by PipelineBuilder)
        workdir: Working directory path
        global_context: Global theme/context for the video
        character: Character name for TTS (optional)
        speed: Speech speed multiplier (default: 1.2)
    """
    text: str
    target_name: str
    project_name: Optional[str] = None  # Will be set by PipelineBuilder
    workdir: str = "."
    global_context: Optional[str] = None
    character: Optional[str] = None
    speed: float = 1.2


# Register schema
register_schema("fish_audio", AudioFishSchema)

