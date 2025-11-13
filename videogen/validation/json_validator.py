
"""
JSON validator for project structure validation.

This validator is to valid project json:
1. whether every block have a text,
2. is there any same id across every block
3. validate project structure and required fields
4. check for missing or malformed data
"""

import json
from typing import Dict, Any, List, Set
from pathlib import Path

try:
    from .base_validator import BaseValidator
except ImportError:
    from base_validator import BaseValidator


class JSONValidator(BaseValidator):
    """Validator for project JSON structure and content."""
    
    def __init__(self):
        super().__init__("json_validator")
    
    def validate(self, project_path: Path) -> Dict[str, Any]:
        """
        Validate project JSON structure and content.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dict containing validation results
        """
        errors = []
        warnings = []
        details = {}
        
        # Get project JSON path
        json_path = self.get_project_json_path(project_path)
        
        # Check if JSON file exists
        if not json_path.exists():
            return {
                "valid": False,
                "errors": [f"Project JSON file not found: {json_path}"],
                "warnings": [],
                "details": {}
            }
        
        try:
            # Load and parse JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"Invalid JSON format: {str(e)}"],
                "warnings": [],
                "details": {}
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Error reading JSON file: {str(e)}"],
                "warnings": [],
                "details": {}
            }
        
        # Validate project structure
        structure_result = self._validate_structure(data)
        errors.extend(structure_result["errors"])
        warnings.extend(structure_result["warnings"])
        details.update(structure_result["details"])
        
        # Validate script blocks
        if "script" in data and isinstance(data["script"], list):
            script_result = self._validate_script_blocks(data["script"], project_path)
            errors.extend(script_result["errors"])
            warnings.extend(script_result["warnings"])
            details.update(script_result["details"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _validate_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic project structure."""
        errors = []
        warnings = []
        details = {}
        
        # Check required fields
        required_fields = ["project", "script"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate project name
        if "project" in data:
            if not isinstance(data["project"], str):
                errors.append("Project name must be a string")
            elif not data["project"].strip():
                errors.append("Project name cannot be empty")
            else:
                details["project_name"] = data["project"]
        
        # Validate script field
        if "script" in data:
            if not isinstance(data["script"], list):
                errors.append("Script must be a list")
            else:
                details["script_count"] = len(data["script"])
                if len(data["script"]) == 0:
                    warnings.append("Script is empty")
        
        # Check for unexpected fields
        expected_fields = {"project", "script", "created_at", "updated_at", "size"}
        unexpected_fields = set(data.keys()) - expected_fields
        if unexpected_fields:
            warnings.append(f"Unexpected fields found: {', '.join(unexpected_fields)}")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _validate_script_blocks(self, script: List[Dict[str, Any]], project_path: Path) -> Dict[str, Any]:
        """Validate individual script blocks."""
        errors = []
        warnings = []
        details = {}
        
        if not script:
            return {"errors": errors, "warnings": warnings, "details": details}
        
        # Track IDs for uniqueness check
        seen_ids: Set[str] = set()
        block_details = []
        
        # Get current working directory to resolve relative paths
        # Paths in JSON are relative to the workspace root
        workdir = Path.cwd()
        
        for i, block in enumerate(script):
            block_errors = []
            block_warnings = []
            block_info = {"index": i}
            # Check if block is a dictionary
            if not isinstance(block, dict):
                block_errors.append(f"Block {i} is not a dictionary")
                block_info["type"] = type(block).__name__
            else:
                # Check required fields for each block
                required_block_fields = ["id", "text"]
                for field in required_block_fields:
                    if field not in block:
                        block_errors.append(f"Block {i} missing required field: {field}")
                    elif field == "text" and not block[field].strip():
                        block_errors.append(f"Block {i} has empty text field")
                
                # Validate ID uniqueness
                if "id" in block:
                    block_id = block["id"]
                    if block_id in seen_ids:
                        block_errors.append(f"Duplicate ID found: {block_id}")
                    else:
                        seen_ids.add(block_id)
                        block_info["id"] = block_id
                
                # Validate text field
                if "text" in block:
                    text = block["text"]
                    if not isinstance(text, str):
                        block_errors.append(f"Block {i} text field must be a string")
                    else:
                        block_info["text_length"] = len(text)
                        if len(text.strip()) == 0:
                            block_errors.append(f"Block {i} has empty text content")
                        elif len(text) > 1000:
                            warnings.append(f"Block {i} has very long text ({len(text)} characters)")
                
                # Validate video_generation result
                if "video_generation" in block:
                    video_gen = block["video_generation"]
                    if not isinstance(video_gen, dict):
                        block_errors.append(f"Block {block.get('id', i)} video_generation must be a dict")
                    else:
                        # Check if ok is true
                        if "ok" not in video_gen:
                            block_errors.append(f"Block {block.get('id', i)} video_generation.ok is missing")
                        elif not video_gen.get("ok", False):
                            block_errors.append(f"Block {block.get('id', i)} video_generation.ok is not true")
                        
                        # Check if meta.output_path exists and file exists
                        if "meta" in video_gen and isinstance(video_gen["meta"], dict):
                            meta = video_gen["meta"]
                            if "output_path" not in meta:
                                block_errors.append(f"Block {block.get('id', i)} video_generation.meta.output_path is missing")
                            else:
                                output_path_str = meta["output_path"]
                                if not isinstance(output_path_str, str) or not output_path_str:
                                    block_errors.append(f"Block {block.get('id', i)} video_generation.meta.output_path is empty")
                                else:
                                    # Check if file exists
                                    output_path = Path(output_path_str)
                                    if not output_path.is_absolute():
                                        # Paths are relative to workspace root
                                        output_path = workdir / output_path_str
                                    if not output_path.exists():
                                        block_errors.append(f"Block {block.get('id', i)} video_generation.meta.output_path file does not exist: {output_path_str}")
                
                # Validate audio_generation result
                if "audio_generation" in block:
                    audio_gen = block["audio_generation"]
                    if not isinstance(audio_gen, dict):
                        block_errors.append(f"Block {block.get('id', i)} audio_generation must be a dict")
                    else:
                        # Check if ok is true
                        if "ok" not in audio_gen:
                            block_errors.append(f"Block {block.get('id', i)} audio_generation.ok is missing")
                        elif not audio_gen.get("ok", False):
                            block_errors.append(f"Block {block.get('id', i)} audio_generation.ok is not true")
                        
                        # Check if meta.audio_path exists and file exists
                        if "meta" in audio_gen and isinstance(audio_gen["meta"], dict):
                            meta = audio_gen["meta"]
                            if "audio_path" not in meta:
                                block_errors.append(f"Block {block.get('id', i)} audio_generation.meta.audio_path is missing")
                            else:
                                audio_path_str = meta["audio_path"]
                                if not isinstance(audio_path_str, str):
                                    block_errors.append(f"Block {block.get('id', i)} audio_generation.meta.audio_path must be a string")
                                else:
                                    # Check if file exists
                                    audio_path = Path(audio_path_str)
                                    if not audio_path.is_absolute():
                                        # Paths are relative to workspace root
                                        audio_path = workdir / audio_path_str
                                    if not audio_path.exists():
                                        block_errors.append(f"Block {block.get('id', i)} audio_generation.meta.audio_path file does not exist: {audio_path_str}")
                
                # Check for optional fields and their types
                optional_fields = {
                    "prompt": str,
                    "context": str,
                    "voice": str,
                    "decision": str,
                    "status": str,
                    "retries": int
                }
                
                for field, expected_type in optional_fields.items():
                    if field in block:
                        if not isinstance(block[field], expected_type):
                            block_warnings.append(f"Block {i} field '{field}' has unexpected type: {type(block[field]).__name__}")
                        else:
                            block_info[field] = f"present ({type(block[field]).__name__})"
            
            # Add block errors to main errors
            errors.extend(block_errors)
            warnings.extend(block_warnings)
            block_details.append(block_info)
        
        details["blocks"] = block_details
        details["unique_ids"] = len(seen_ids)
        details["total_blocks"] = len(script)
        
        # Check for ID patterns
        id_patterns = {}
        for block_id in seen_ids:
            if block_id.startswith("L"):
                id_patterns["L_prefix"] = id_patterns.get("L_prefix", 0) + 1
            elif block_id.isdigit():
                id_patterns["numeric"] = id_patterns.get("numeric", 0) + 1
            else:
                id_patterns["other"] = id_patterns.get("other", 0) + 1
        
        if id_patterns:
            details["id_patterns"] = id_patterns
        
        return {
            "errors": errors,
            "warnings": warnings,
            "details": details
        }