import json
from pathlib import Path
from typing import Any, Dict, Optional

from dacite import from_dict

from wiki2video.core.paths import get_project_json_path
from wiki2video.schema.project_schema import ProjectStatus, ProjectJSON


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input JSON not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)

def get_project_status(raw: Dict[str, Any]) -> ProjectStatus:
    """Get project status from JSON data, default to CREATED if not set."""
    status_str = raw.get("project_status")
    if status_str:
        try:
            return ProjectStatus(status_str)
        except ValueError:
            return ProjectStatus.CREATED
    return ProjectStatus.CREATED

def set_project_status(project_id: str, status: ProjectStatus) -> None:
    """Update project status in JSON file."""
    json_path = get_project_json_path(project_id)
    raw = read_json(json_path)
    raw["project_status"] = status.value
    write_json(json_path, raw)


def parse_project(project_id: str) -> ProjectJSON:
    json_path = get_project_json_path(project_id)
    raw = read_json(json_path)
    project_name = raw.get("project_name")
    if not project_name:
        raise RuntimeError("Missing project_name in JSON")

    raw.setdefault("project_id", project_id)

    if "project_status" in raw and isinstance(raw["project_status"], str):
        try:
            raw["project_status"] = ProjectStatus(raw["project_status"])
        except ValueError:
            raw["project_status"] = ProjectStatus.CREATED

    project = from_dict(ProjectJSON, raw)
    return project
