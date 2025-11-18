"""
SchemaRegistry - Registry for ActionSchema classes.
Similar to MethodRegistry, but only stores schema classes (not handlers).
"""
from typing import Type, Dict, TypeVar
from dataclasses import dataclass

# Type variable for schema classes
T = TypeVar('T', bound=dataclass)

# Global registry: method_name -> schema_class
_SCHEMA_REGISTRY: Dict[str, Type[T]] = {}


def register_schema(method_name: str, schema_class: Type[T]) -> Type[T]:
    """
    Register a schema class for a method.
    
    Args:
        method_name: The method name (must match Method.NAME)
        schema_class: The schema dataclass class
        
    Returns:
        The schema class (for chaining)
        
    Raises:
        ValueError: If method_name is already registered
    """
    if method_name in _SCHEMA_REGISTRY:
        raise ValueError(f"Schema for method '{method_name}' already registered.")
    _SCHEMA_REGISTRY[method_name] = schema_class
    return schema_class


def get_schema(method_name: str) -> Type[T]:
    """
    Get schema class for a method.
    
    Args:
        method_name: The method name
        
    Returns:
        The schema class
        
    Raises:
        KeyError: If schema not found
    """
    if method_name not in _SCHEMA_REGISTRY:
        raise KeyError(
            f"Schema for method '{method_name}' not found. "
            f"Registered: {list(_SCHEMA_REGISTRY.keys())}"
        )
    return _SCHEMA_REGISTRY[method_name]


def has_schema(method_name: str) -> bool:
    """
    Check if a schema is registered for a method.
    
    Args:
        method_name: The method name
        
    Returns:
        True if schema exists, False otherwise
    """
    return method_name in _SCHEMA_REGISTRY


def list_schemas() -> Dict[str, Type[T]]:
    """
    List all registered schemas.
    
    Returns:
        Dictionary mapping method names to schema classes
    """
    return dict(_SCHEMA_REGISTRY)

