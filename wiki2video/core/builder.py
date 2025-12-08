"""
Pipeline Builder - Convert ActionSpec[] into WorkingBlock rows.
DEPRECATED: This file is no longer used. Pipeline.build() now handles this directly.
"""
import json
import uuid
from typing import List, Dict
from pathlib import Path

from wiki2video.schema.action_spec import ActionSpec
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus


def build_working_blocks(action_specs: List[ActionSpec]) -> List[WorkingBlock]:
    """
    Convert a list of ActionSpec into WorkingBlock rows.
    DEPRECATED: Use Pipeline.build() instead.
    
    This function now builds chain dependencies automatically.
    
    Args:
        action_specs: List of ActionSpec in execution order
        
    Returns:
        List of WorkingBlock instances
    """
    working_blocks = []
    prev_working_id = None
    
    for action_index, action in enumerate(action_specs):
        # Build prev_ids (chain dependency)
        prev_working_ids = []
        if prev_working_id:
            prev_working_ids = [prev_working_id]
        
        # Create working block
        config = action.config or {}
        working_block = WorkingBlock(
            id=str(uuid.uuid4()),
            project_id=config.get("project_id", "default"),
            method_name=action.type,
            status=WorkingBlockStatus.PENDING,
            prev_ids=prev_working_ids,
            action_index=action_index,  # Add action_index support
            config_json=json.dumps(config, ensure_ascii=False)
        )
        
        working_blocks.append(working_block)
        prev_working_id = working_block.id
    
    return working_blocks
