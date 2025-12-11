# llm_agent/agents/utils/svg_converter.py
import cairosvg
from pathlib import Path
import re

def sanitize_filename(name: str) -> str:
    """Remove or replace unsafe characters."""
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w\.-]", "_", name)
    return name


def convert_svg_to_png(svg_path: Path) -> Path:
    """
    Convert SVG → PNG.
    Returns PNG path.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    png_path = svg_path.with_suffix(".png")

    # Already converted
    if png_path.exists():
        return png_path

    # Convert
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))
    print(f"    🟢 SVG converted → PNG: {png_path}")

    return png_path


def ensure_non_svg(path: Path) -> Path:
    """
    If file is SVG → convert and return PNG.
    Otherwise → return original path.
    """
    if path.suffix.lower() == ".svg":
        return convert_svg_to_png(path)
    return path
