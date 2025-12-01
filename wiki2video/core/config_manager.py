#!/usr/bin/env python3
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, Optional


class ConfigManager:
    """
    Global singleton-style configuration manager.
    - Loads from .env once and caches values
    - Provides fallback defaults
    - Persists updates back to .env
    """

    _lock = threading.RLock()
    _cache: Dict[str, str] = {}
    _order: Dict[str, None] = {}
    _loaded = False

    _DEFAULTS: Dict[str, str] = {
        "SILICONFLOW_API_TOKEN": "",
        "LLM_DEFAULT_MODEL": "deepseek-ai/DeepSeek-V3",
        "AUDIO_FISH_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "GOOGLE_CX_KEY": "",
        "TIKTOK_FORMAT_PICTURE_WIDTH_RATIO": "0.4",
        "TIKTOK_FORMAT_PICTURE_X_RATIO": "0.02",
        "TIKTOK_FORMAT_PICTURE_Y_RATIO": "0.78",
        "TIKTOK_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO": "0.1",
        "LANDSCAPE_FORMAT_PICTURE_WIDTH_RATIO": "0.15",
        "LANDSCAPE_FORMAT_PICTURE_X_RATIO": "0.02",
        "LANDSCAPE_FORMAT_PICTURE_Y_RATIO": "0.78",
        "LANDSCAPE_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO": "0.1",
        "FONT_PATH": "assets/microhei.ttc",
    }

    _ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._loaded:
            return
        cls.reload()

    @classmethod
    def reload(cls) -> None:
        """Reload .env file into cache and os.environ."""
        with cls._lock:
            data: Dict[str, str] = {}
            order: Dict[str, None] = {}

            if cls._ENV_PATH.exists():
                for line in cls._ENV_PATH.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or "=" not in stripped:
                        continue
                    key, value = stripped.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    data[key] = value
                    order[key] = None
            else:
                cls._ENV_PATH.touch()

            cls._cache = data
            cls._order = order
            cls._loaded = True

            for key, value in data.items():
                os.environ[key] = value

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> str:
        """Read a config value with fallback to defaults."""
        cls._ensure_loaded()
        if key in os.environ:
            return os.environ[key]
        if key in cls._cache:
            return cls._cache[key]
        if key in cls._DEFAULTS:
            return cls._DEFAULTS[key]
        if default is not None:
            return default
        return ""

    @classmethod
    def set(cls, key: str, value: Optional[str]) -> None:
        """Persist a config value to .env and refresh cache."""
        cls._ensure_loaded()
        str_value = "" if value is None else str(value)
        with cls._lock:
            cls._cache[key] = str_value
            cls._order.setdefault(key, None)
            os.environ[key] = str_value
            cls._write_env_file()

    @classmethod
    def all(cls) -> Dict[str, str]:
        """Return a merged view of cache + defaults."""
        cls._ensure_loaded()
        keys = set(cls._DEFAULTS.keys()) | set(cls._cache.keys())
        return {key: cls.get(key) for key in sorted(keys)}

    @classmethod
    def _write_env_file(cls) -> None:
        """Write the current cache into the .env file preserving order."""
        lines = []
        seen = set()
        for key in cls._order:
            if key in cls._cache:
                value = cls._cache[key]
                escaped = cls._escape(value)
                lines.append(f"{key}={escaped}")
                seen.add(key)

        for key, value in cls._cache.items():
            if key in seen:
                continue
            escaped = cls._escape(value)
            lines.append(f"{key}={escaped}")

        cls._ENV_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    @staticmethod
    def _escape(value: str) -> str:
        if not value:
            return ""
        if any(ch.isspace() for ch in value) or "#" in value:
            return f'"{value}"'
        return value


