
"""
Project validator backed by WorkingBlock SQLite data.

This validator inspects WorkingBlocks stored in SQLite (via WorkingBlockDAO) to
ensure every block/action has the required metadata (block_id, deterministic
output directory under project/{project}/blocks/..., meta traces, etc.).
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from .base_validator import BaseValidator
except ImportError:
    from base_validator import BaseValidator

from wiki2video.dao.working_block_dao import WorkingBlockDAO


class JSONValidator(BaseValidator):
    """Validator that checks WorkingBlocks stored in SQLite."""
    
    def __init__(self):
        super().__init__("json_validator")
        self._dao = WorkingBlockDAO()
    
    def validate(self, project_path: Path) -> Dict[str, Any]:
        """
        Validate project data using WorkingBlocks stored in SQLite.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dict containing validation results
        """
        project_name = project_path.name
        working_blocks = self._dao.get_all(project_name)
        
        if not working_blocks:
            return {
                "valid": False,
                "errors": [f"No working blocks found for project '{project_name}' in SQLite"],
                "warnings": [],
                "details": {"project_name": project_name}
            }
        
        validation = self._validate_working_blocks(project_path, project_name, working_blocks)
        
        return validation
    
    def _validate_working_blocks(
        self,
        project_path: Path,
        project_name: str,
        working_blocks
    ) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {
            "project_name": project_name,
            "working_block_count": len(working_blocks),
        }
        
        blocks_root = project_path / "blocks"
        if not blocks_root.exists():
            warnings.append(f"Blocks directory not found: {blocks_root}")
        
        block_details: List[Dict[str, Any]] = []
        seen_working_block_ids = set()
        
        for wb in working_blocks:
            wb_errors: List[str] = []
            wb_warnings: List[str] = []
            wb_info: Dict[str, Any] = {
                "working_block_id": wb.id,
                "method": wb.method_name,
                "block_id": wb.block_id,
                "status": wb.status.value if wb.status else None,
            }
            
            if wb.id in seen_working_block_ids:
                wb_warnings.append(f"Duplicate working block ID detected: {wb.id}")
            else:
                seen_working_block_ids.add(wb.id)
            
            if not wb.block_id:
                wb_errors.append(f"WorkingBlock {wb.id} missing block_id (target_name)")
            
            expected_action_dir = None
            if wb.block_id:
                expected_action_dir = blocks_root / wb.block_id / wb.method_name / wb.id
                wb_info["expected_action_dir"] = str(expected_action_dir)
                if not expected_action_dir.exists():
                    wb_warnings.append(f"Action directory not found: {expected_action_dir}")
            
            output_path = None
            if wb.output_path:
                output_path = Path(wb.output_path)
                if not output_path.is_absolute():
                    output_path = Path.cwd() / output_path
                wb_info["output_path"] = str(output_path)
                
                if expected_action_dir and not self._path_within(output_path, expected_action_dir):
                    wb_errors.append(
                        f"Output for working block {wb.id} is outside expected directory {expected_action_dir}: {output_path}"
                    )
                
                if not output_path.exists():
                    wb_errors.append(f"Output file does not exist for working block {wb.id}: {output_path}")
                
                meta_path = (output_path.parent / "meta.json") if output_path else None
                if meta_path:
                    wb_info["meta_path"] = str(meta_path)
                    if not meta_path.exists():
                        wb_warnings.append(f"meta.json missing for working block {wb.id}: {meta_path}")
            else:
                wb_warnings.append(f"WorkingBlock {wb.id} has no output_path recorded")
            
            if wb_errors:
                errors.extend(wb_errors)
            if wb_warnings:
                warnings.extend(wb_warnings)
            
            wb_info["errors"] = wb_errors
            wb_info["warnings"] = wb_warnings
            block_details.append(wb_info)
        
        details["working_blocks"] = block_details
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }

    @staticmethod
    def _path_within(path: Path, parent: Path) -> bool:
        """Return True if path is inside parent directory."""
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False