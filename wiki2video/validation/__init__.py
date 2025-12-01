"""
Videogen validation module.

This module provides validation functionality for videogen projects, including:
- Base validator class and registry
- JSON structure validation
- SiliconFlow account validation
"""

from .base_validator import (
    BaseValidator,
    ValidationRegistry,
    get_global_registry,
    validate_project,
    main
)
from .json_validator import JSONValidator
from .silicon_flow_account_validator import SiliconFlowAccountValidator

__all__ = [
    # Base classes
    "BaseValidator",
    "ValidationRegistry",
    
    # Validators
    "JSONValidator",
    "SiliconFlowAccountValidator",
    
    # Registry functions
    "get_global_registry",
    "validate_project",
    "main"
]
