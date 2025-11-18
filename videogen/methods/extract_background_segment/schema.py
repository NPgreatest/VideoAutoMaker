"""
ActionSchema for extract_background_segment method.
"""
from dataclasses import dataclass
from videogen.schema.schema_registry import register_schema


@dataclass
class ExtractBackgroundSegmentSchema:
    """
    Schema for extract_background_segment method configuration.
    
    Attributes:
        start_time: Start time in seconds
        end_time: End time in seconds (optional, can use duration_ms instead)
        project_name: Project name
        target_name: Target video file name
        workdir: Working directory path
        duration_ms: Duration in milliseconds (optional, can use end_time instead)
    """
    start_time: float = 0.0
    end_time: float = None
    project_name: str = None
    target_name: str = None
    workdir: str = "."
    duration_ms: float = None


# Register schema
register_schema("extract_background_segment", ExtractBackgroundSegmentSchema)

