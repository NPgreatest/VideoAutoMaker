#!/usr/bin/env python3
"""
Path utilities for the new hierarchical file structure.

All file I/O paths should use these utilities to ensure consistency.
"""
from pathlib import Path


def get_action_output_dir(
    project_root: Path,
    project_name: str,
    block_id: str,
    method_name: str,
    working_block_id: str
) -> Path:
    """
    Get the deterministic working directory for a working block under:
    {project_root}/project/{project_name}/blocks/{block_id}/{method_name}/{working_block_id}/
    
    Args:
        project_root: Root directory (usually workdir)
        project_name: Project identifier under /project/
        block_id: ScriptBlock.id (e.g., "L1")
        method_name: BaseMethod.NAME (e.g., "fish_audio", "remotion_picture")
        working_block_id: WorkingBlock.id (unique UUID)
        
    Returns:
        Path to the working block output directory
    """
    action_dir = (
        project_root
        / "project"
        / project_name
        / "blocks"
        / block_id
        / method_name
        / working_block_id
    )
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

