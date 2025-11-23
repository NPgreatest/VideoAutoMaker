import requests
from pathlib import Path


def download_images(urls: list[str], save_dir: Path) -> list[Path]:
    """
    Download each URL to save_dir. Return list of saved paths (same order).
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    for i, url in enumerate(urls):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            ext = ".jpg"
            path = save_dir / f"rank_{i}{ext}"
            with open(path, "wb") as f:
                f.write(r.content)

            saved_paths.append(path)

        except Exception:
            continue

    return saved_paths

