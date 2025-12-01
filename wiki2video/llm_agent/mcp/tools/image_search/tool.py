from pathlib import Path
from typing import Any

from .search import google_image_search
from .downloader import download_images


class ImageSearchTool:
    name = "image_search"
    description = "Search images via Google API and save best + alternatives by ranking"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "project_name": {"type": "string"},
            "target_name": {"type": "string"}
        },
        "required": ["query", "project_name", "target_name"]
    }

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments["query"]
        project_name = arguments["project_name"]
        target_name = arguments["target_name"]

        images_root = Path(f"project/{project_name}/images")
        images_root.mkdir(parents=True, exist_ok=True)

        # 1. Google search
        urls = google_image_search(query)
        if not urls:
            return {"error": "No Google results"}

        target_path = Path(target_name)
        suffix = target_path.suffix or ".jpg"
        stem = target_path.stem if target_path.suffix else target_path.name
        main_filename = f"{stem}{suffix}"
        alt_filenames = [f"{stem}_{i}{suffix}" for i in range(1, 4)]  # top 3 alternatives
        max_needed = 1 + len(alt_filenames)

        # 2. Download top results directly to desired filenames
        downloaded_paths = download_images(
            urls,
            images_root,
            filenames=[main_filename] + alt_filenames,
            limit=max_needed,
        )
        if not downloaded_paths:
            return {"error": "No images downloaded"}

        # Ensure all are Paths
        downloaded_paths = [Path(p) for p in downloaded_paths]

        main_dest = downloaded_paths[0]
        final_alts = downloaded_paths[1:]

        return {
            "best": str(main_dest),
            "alternatives": [str(p) for p in final_alts]
        }
