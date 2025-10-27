import abc
from pathlib import Path
from typing import Dict, Any

class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override
    OUTPUT_KIND: str = "any"  # "audio" | "video" | "other"

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def run(self, *, project: str, target_name: str, text: str, workdir: Path, duration_ms: int | None = None, block) -> Dict[str, Any]:
        """Execute the method and return a dict:
        {{
          "ok": bool,
          "artifacts": [<paths>],
          "meta": {{...}},
          "error": <str or None>
        }}
        """
        raise NotImplementedError


    def generate_prompt(self, text: str, context: str = None) -> str:
        """Execute the method and return a str:
        prompt...
        """
        raise NotImplementedError