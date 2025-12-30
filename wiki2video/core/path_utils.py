#!/usr/bin/env python3
"""
Path utilities for the new hierarchical file structure.

All file I/O paths should use these utilities to ensure consistency.
"""
from pathlib import Path

from wiki2video.core.paths import get_projects_root


def get_action_output_dir(
    project_id: str,
    block_id: str,
    method_name: str,
    working_block_id: str
) -> Path:
    """
    Get the deterministic working directory for a working block under:
    {projects_root}/{project_id}/blocks/{block_id}/{method_name}/{working_block_id}/
    
    Args:
        project_id: Project identifier
        block_id: ScriptBlock.id (e.g., "L1")
        method_name: BaseMethod.NAME (e.g., "text_audio", "remotion_picture")
        working_block_id: WorkingBlock.id (unique UUID)
        
    Returns:
        Path to the working block output directory
    """
    projects_root = get_projects_root()
    action_dir = (
        projects_root
        / project_id
        / "blocks"
        / block_id
        / method_name
        / working_block_id
    )
    action_dir.mkdir(parents=True, exist_ok=True)
    return action_dir


def get_output_file_path(
    action_dir: Path,
    block_id: str,
    extension: str = "mp4"
) -> Path:
    """
    Get the standard output file path within an action directory.
    """
    return action_dir / f"{block_id}.{extension}"


def get_meta_file_path(action_dir: Path) -> Path:
    """
    Get the meta.json file path within an action directory.
    
    Args:
        action_dir: Action output directory
        
    Returns:
        Path to meta.json: {action_dir}/meta.json
    """
    return action_dir / "meta.json"
