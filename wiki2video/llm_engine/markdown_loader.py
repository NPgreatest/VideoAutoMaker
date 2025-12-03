"""Markdown prompt 加载/Registry 工具。

提供统一的路径解析、缓存，便于 Agent 读取共享 prompt。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping


def load_markdown(path: str) -> str:
    """读取 markdown 文件正文，预留 YAML front matter 解析接口。"""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


class MarkdownPromptLoader:
    """Markdown 模板与 registry 的统一读取入口。"""

    REGISTRY_FILENAME = "registry.json"

    def __init__(self) -> None:
        default_dir = Path(__file__).resolve().parents[0] / "prompts"
        self.base_dir = default_dir
        if not self.base_dir.exists():
            raise FileNotFoundError(f"Prompt 目录不存在: {self.base_dir}")
        self.registry_path = default_dir / self.REGISTRY_FILENAME

    def _resolve(self, relative_path: str) -> Path:
        path = (self.base_dir / relative_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"未找到 prompt 文件: {path}")
        if not path.is_file():
            raise ValueError(f"Prompt 路径不是文件: {path}")
        return path

    @lru_cache(maxsize=1)
    def _load_registry(self) -> Dict[str, Dict[str, str]]:
        if not self.registry_path.exists():
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def list_registry(self) -> Mapping[str, Dict[str, str]]:
        """供前端/后端读取 registry 内容，驱动下拉菜单。"""
        return self._load_registry()

    @lru_cache(maxsize=64)
    def load_from_registry(self, category: str, key: str) -> str:
        """根据 registry 的分类与 key 获取模板正文。"""
        registry = self._load_registry()
        category_data = registry.get(category)
        if category_data is None:
            raise KeyError(f"Registry 中不存在分类: {category}")
        relative_path = category_data.get(key)
        if relative_path is None:
            raise KeyError(f"Registry 分类 {category} 中不存在 {key}")
        path = self._resolve(relative_path)
        return load_markdown(str(path))


__all__ = ["MarkdownPromptLoader", "load_markdown"]
