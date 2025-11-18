"""
ActionSpec - Project JSON representation of an action.
"""
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class ActionSpec:
    """
    Action specification stored in project JSON.
    
    Attributes:
        id: Unique identifier for this action
        type: Method name (maps to Method.NAME)
        prev_ids: List of previous action IDs (empty list for first action)
        config: Raw configuration dictionary (will be parsed by ActionSchema)
    """
    id: str
    type: str  # Maps to Method.NAME
    prev_ids: List[str] = None  # Multiple upstream dependencies
    config: Dict[str, Any] = None  # Raw config dict
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.prev_ids is None:
            self.prev_ids = []

