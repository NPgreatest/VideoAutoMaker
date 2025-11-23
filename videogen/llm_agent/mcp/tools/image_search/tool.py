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

        # 2. Download top results
        downloaded_paths = download_images(urls, images_root)
        if not downloaded_paths:
            return {"error": "No images downloaded"}

        # Ensure all are Paths
        downloaded_paths = [Path(p) for p in downloaded_paths]

        # 3. Rename main image → target_name
        main_src = downloaded_paths[0]
        main_dest = images_root / target_name

        # If main_dest already exists, delete it first
        if main_dest.exists():
            main_dest.unlink()

        main_src.rename(main_dest)

        # 4. Rename alternatives to P1_1.png, P1_2.png...
        stem = Path(target_name).stem      # P1
        suffix = Path(target_name).suffix  # .png, .jpg...

        alts = downloaded_paths[1:4]  # top 3 as alternatives
        final_alts = []

        for i, src in enumerate(alts, start=1):
            dest = images_root / f"{stem}_{i}{suffix}"

            if dest.exists():
                dest.unlink()

            src.rename(dest)
            final_alts.append(dest)

        return {
            "best": str(main_dest),
            "alternatives": [str(p) for p in final_alts]
        }
