"""
Abstract worker interface for method classes.
Methods that need background processing can implement this interface.
"""

from abc import ABC, abstractmethod

from wiki2video.core.working_block import WorkingBlock


class WorkerInterface(ABC):
    """Interface for methods that need background processing."""
    
    @abstractmethod
    def process_working_block(self, working_block: WorkingBlock) -> bool:
        """
        Process a WorkingBlock in the background.
        
        Args:
            working_block: The WorkingBlock to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_worker_name(self) -> str:
        """
        Get the name of this worker for registration.
        
        Returns:
            str: Worker name (usually matches method NAME)
        """
        pass
    
    def supports_background_processing(self) -> bool:
        """
        Check if this method supports background processing.
        
        Returns:
            bool: True if this method supports background processing
        """
        return True
