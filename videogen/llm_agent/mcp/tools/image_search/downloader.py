import requests
from pathlib import Path
from urllib.parse import urlparse


def _infer_ext(url: str, fallback: str = ".jpg") -> str:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext and len(ext) <= 5:
        return ext
    return fallback


def download_images(
    urls: list[str],
    save_dir: Path,
    *,
    filenames: list[str] | None = None,
    limit: int | None = None,
) -> list[Path]:
    """
    Download URLs to save_dir using provided filenames (if any).
    Returns list of saved paths in order.
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    max_count = limit if limit is not None else len(urls)
    for i, url in enumerate(urls):
        if i >= max_count:
            break
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            ext = _infer_ext(url)
            if filenames and i < len(filenames) and filenames[i]:
                candidate = Path(filenames[i])
                path = save_dir / (candidate if candidate.suffix else candidate.with_suffix(ext))
            else:
                path = save_dir / f"rank_{i}{ext}"

            if path.exists():
                path.unlink()

            with open(path, "wb") as f:
                f.write(r.content)

            saved_paths.append(path)

        except Exception:
            continue

    return saved_paths

