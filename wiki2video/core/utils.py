import json
from pathlib import Path
from typing import Any, Dict, Optional

from dacite import from_dict

from wiki2video.config.config_vars import WORKING_DIR
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

def load_character_config() -> Dict[str, Any]:
    """
    从 config/character_config.json 读取角色配置。
    返回格式: {character_name: {name, model_id, image_path}}
    """
    cfg_path = Path("config/character_config.json")
    if not cfg_path.exists():
        return {}
    try:
        return read_json(cfg_path)
    except Exception as e:
        print(f"[character_config] ⚠️ Failed to load character config: {e}")
        return {}

def get_character_info(character: str) -> Optional[Dict[str, Any]]:
    if not character:
        return None
    
    config = load_character_config()
    
    # 直接匹配
    if character in config:
        return config[character]
    
    # 尝试映射：常见缩写映射
    mapping = {
        "hu": "huchenfeng",
    }
    
    mapped_character = mapping.get(character)
    if mapped_character and mapped_character in config:
        return config[mapped_character]
    
    return None

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
    raw = read_json(WORKING_DIR / project_id / f"{project_id}.json")
    raw["project_status"] = status.value
    write_json(WORKING_DIR / project_id / f"{project_id}.json", raw)


def parse_project(project_id: str) -> ProjectJSON:
    raw = read_json(WORKING_DIR / project_id / f"{project_id}.json")
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
