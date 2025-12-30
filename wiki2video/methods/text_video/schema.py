"""
ActionSchema for text_to_video method.
"""
from dataclasses import dataclass
from wiki2video.schema.schema_registry import register_schema


@dataclass
class TextToVideoSchema:
    """
    Schema for text_to_video method configuration.
    
    Attributes:
        text: Original text content
        prompt: Text prompt for video generation (generated from text if not provided)
        project_id: Project id
        target_name: Target video file name
        image_size: Image size for video generation (e.g., "1280x720")
        request_id: Request ID from API (set during poll)
        global_context: Global theme/context for the entire video
    """
    text: str
    prompt: str = None
    project_id: str = None
    target_name: str = None
    image_size: str = None
    request_id: str = None
    global_context: str = None


# Register schema
register_schema("text_video", TextToVideoSchema)
