from pathlib import Path
import platform
import os


def get_app_data_dir() -> Path:
    system = platform.system()

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "wiki2video"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "wiki2video"
    else:
        return Path.home() / ".local" / "share" / "wiki2video"


def get_db_path() -> Path:
    base = get_app_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / "working_blocks.db"



def get_projects_root() -> Path:
    root = get_app_data_dir() / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_project_dir(project_id: str) -> Path:
    """
    Get the project directory for a given project_id.
    All project-specific files should be stored under this directory.
    
    Args:
        project_id: Project identifier
        
    Returns:
        Path to the project directory: {projects_root}/{project_id}
    """
    project_dir = get_projects_root() / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def get_project_json_path(project_id: str) -> Path:
    """
    Get the path to the project JSON file.
    
    Args:
        project_id: Project identifier
        
    Returns:
        Path to {project_dir}/{project_id}.json
    """
    return get_project_dir(project_id) / f"{project_id}.json"


