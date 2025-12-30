
"""
Base validator class for the videogen validation system.

This is the base class of validator, every validator should extend this class.
This base class need to have abstract method of validate, and make a global validator
instance, every file can use the validator list or function to validate the project,
the entry point is just the project name provided on the command line.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

from wiki2video.core.paths import get_project_dir


class BaseValidator(ABC):
    """Base class for all validators in the videogen system."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def validate(self, project_path: Path) -> Dict[str, Any]:
        """
        Validate a project and return validation results.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dict containing validation results with keys:
            - valid: bool - whether validation passed
            - errors: List[str] - list of error messages
            - warnings: List[str] - list of warning messages
            - details: Dict[str, Any] - additional validation details
        """
        pass
    
    def get_project_json_path(self, project_path: Path) -> Path:
        """Get the path to the project JSON file."""
        project_name = project_path.name
        return project_path / f"{project_name}.json"


class ValidationRegistry:
    """Global registry for all validators."""
    
    def __init__(self):
        self._validators: Dict[str, BaseValidator] = {}
    
    def register(self, validator: BaseValidator) -> None:
        """Register a validator."""
        self._validators[validator.name] = validator
    
    def get_validator(self, name: str) -> Optional[BaseValidator]:
        """Get a validator by name."""
        return self._validators.get(name)
    
    def get_all_validators(self) -> List[BaseValidator]:
        """Get all registered validators."""
        return list(self._validators.values())
    
    def validate_project(self, project_path: Path, validator_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate a project using specified validators or all validators.
        
        Args:
            project_path: Path to the project directory
            validator_names: List of validator names to use, or None for all
            
        Returns:
            Dict containing combined validation results
        """
        if validator_names is None:
            validators = self.get_all_validators()
        else:
            validators = [self.get_validator(name) for name in validator_names if self.get_validator(name)]
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "details": {},
            "validator_results": {}
        }
        
        for validator in validators:
            try:
                result = validator.validate(project_path)
                results["validator_results"][validator.name] = result
                
                if not result.get("valid", False):
                    results["valid"] = False
                
                results["errors"].extend(result.get("errors", []))
                results["warnings"].extend(result.get("warnings", []))
                results["details"][validator.name] = result.get("details", {})
                
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"Validator {validator.name} failed: {str(e)}")
                results["validator_results"][validator.name] = {
                    "valid": False,
                    "errors": [str(e)],
                    "warnings": [],
                    "details": {}
                }
        
        return results


# Global validator registry instance
_global_registry = ValidationRegistry()


def get_global_registry() -> ValidationRegistry:
    """Get the global validator registry."""
    return _global_registry


def validate_project(project_name: str, validator_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate a project by name using the global registry.
    
    Args:
        project_name: Name of the project to validate
        validator_names: List of validator names to use, or None for all
        
    Returns:
        Dict containing validation results
    """
    project_path = get_project_dir(project_name)
    if not project_path.exists():
        return {
            "valid": False,
            "errors": [f"Project directory not found: {project_path}"],
            "warnings": [],
            "details": {},
            "validator_results": {}
        }
    
    return _global_registry.validate_project(project_path, validator_names)


def main():
    """Main function to validate a specific project."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate a wiki2video project.")
    parser.add_argument("project_name", help="Name of the project")
    args = parser.parse_args()
    project_name = args.project_name
    
    print(f"🔍 Validating project: {project_name}")
    
    # Import and register all validators
    try:
        # Try relative imports first (when used as module)
        from .json_validator import JSONValidator
        from .silicon_flow_account_validator import SiliconFlowAccountValidator
    except ImportError:
        # Fall back to absolute imports (when run directly)
        from json_validator import JSONValidator
        from silicon_flow_account_validator import SiliconFlowAccountValidator
    
    # Register validators
    _global_registry.register(JSONValidator())
    _global_registry.register(SiliconFlowAccountValidator())
    
    # Validate project
    results = validate_project(project_name)
    
    # Print results
    if results["valid"]:
        print("✅ Project validation passed!")
    else:
        print("❌ Project validation failed!")
    
    if results["errors"]:
        print("\n🚨 Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    if results["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    
    # Print detailed results for each validator
    print("\n📊 Detailed Results:")
    for validator_name, result in results["validator_results"].items():
        print(f"\n{validator_name}:")
        print(f"  Valid: {result.get('valid', False)}")
        if result.get("errors"):
            print(f"  Errors: {result['errors']}")
        if result.get("warnings"):
            print(f"  Warnings: {result['warnings']}")
        if result.get("details"):
            print(f"  Details: {result['details']}")


if __name__ == "__main__":
    main()
