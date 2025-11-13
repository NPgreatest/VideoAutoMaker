import abc
from pathlib import Path
from typing import Dict, Any, Optional
from videogen.pipeline.schema import WorkingBlock, WorkingBlockStatus, ScriptBlock
from videogen.dao.working_block_dao import WorkingBlockDAO
import uuid


class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override
    OUTPUT_KIND: str = "any"  # "audio" | "video" | "other"

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def run(self, *, project: str, target_name: str, text: str, workdir: Path, duration_ms: int | None = None, block) -> Dict[str, Any]:
        """Execute the method and return a dict:
        {
          "ok": bool,
          "artifacts": [<paths>],
          "meta": {...},
          "error": <str or None>
        }
        """
        raise NotImplementedError

    def generate_prompt(self, text: str, context: str = None) -> str:
        """Execute the method and return a str:
        prompt...
        """
        raise NotImplementedError
    
    def supports_background_processing(self) -> bool:
        """
        Check if this method supports background processing.
        Override this method to return True if the method supports background processing.
        
        Returns:
            bool: True if this method supports background processing
        """
        return False
    
    def create_working_block(self, project: str, target_name: str, workdir: Path, block: Optional[ScriptBlock] = None) -> Optional[str]:
        """
        Create a WorkingBlock for background processing.
        This method should be called by run() when the method supports background processing.
        
        Args:
            project: Project name
            target_name: Target name
            workdir: Working directory
            block: ScriptBlock (optional)
            
        Returns:
            str: Working ID if successful, None otherwise
        """
        if not self.supports_background_processing():
            return None
        
        working_id = str(uuid.uuid4())
        
        # Update block with working_id
        if block:
            block.working_id = working_id
        
        # Create WorkingBlock
        working_block = WorkingBlock(
            working_id=working_id,
            project_id=project,
            output_folder=str(workdir),
            block=block,
            status=WorkingBlockStatus.PENDING,
            method_name=self.NAME  # Store the method name for processing
        )
        
        # Store in SQLite database
        dao = WorkingBlockDAO()
        success = dao.create_working_block(working_block)
        
        if success:
            return working_id
        else:
            return None
    
    def process_working_block(self, working_block: WorkingBlock) -> bool:
        """
        Process a WorkingBlock in the background.
        This method should be overridden by methods that support background processing.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Default implementation - methods should override this
        return False
    
    def get_worker_name(self) -> str:
        """
        Get the name of this worker for registration.
        
        Returns:
            str: Worker name (usually matches method NAME)
        """
        return self.NAME