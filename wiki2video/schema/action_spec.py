"""
ActionSpec - Project JSON representation of an action.
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ActionSpec:
    """
    Action specification stored in project JSON.
    
    Attributes:
        type: Method name (maps to Method.NAME)
        config: Raw configuration dictionary (will be parsed by ActionSchema)
    """
    type: str  # Maps to Method.NAME
    config: Dict[str, Any] = None  # Raw config dict
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}

