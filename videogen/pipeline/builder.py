"""
Pipeline Builder - Convert ActionSpec[] into WorkingBlock rows.
"""
import json
from typing import List, Dict
from pathlib import Path

from videogen.schema.action_spec import ActionSpec
from videogen.pipeline.working_block import WorkingBlock, WorkingBlockStatus


def build_working_blocks(action_specs: List[ActionSpec]) -> List[WorkingBlock]:
    """
    Convert a list of ActionSpec into WorkingBlock rows.
    Assigns prev_ids based on action dependencies.
    
    Args:
        action_specs: List of ActionSpec in execution order
        
    Returns:
        List of WorkingBlock instances
    """
    working_blocks = []
    
    # Build maps for quick lookup
    action_map: Dict[str, ActionSpec] = {action.id: action for action in action_specs}
    action_id_to_working_id: Dict[str, str] = {}  # action_id -> working_block.id
    
    for action in action_specs:
        # Determine prev_working_ids
        prev_working_ids = []
        for prev_action_id in action.prev_ids:
            prev_working_id = action_id_to_working_id.get(prev_action_id)
            if prev_working_id:
                prev_working_ids.append(prev_working_id)
        
        # Create working block
        working_block = WorkingBlock(
            id=f"wb_{action.id}",  # Generate unique ID
            action_id=action.id,
            method_name=action.type,
            status=WorkingBlockStatus.PENDING,
            retries=0,
            output_path=None,
            prev_ids=prev_working_ids,
            config_json=json.dumps(action.config, ensure_ascii=False)
        )
        
        working_blocks.append(working_block)
        
        # Update mapping for future lookups
        action_id_to_working_id[action.id] = working_block.id
    
    return working_blocks

