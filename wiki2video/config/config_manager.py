#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

from wiki2video.config.default_config import _default_config
from wiki2video.config.support_platform import SUPPORTED_PLATFORMS

# ======================================================================
# Paths
# ======================================================================
CONFIG_DIR = Path.home() / ".config" / "wiki2video"
CONFIG_FILE = CONFIG_DIR / "config.json"




# ======================================================================
# Config Manager
# ======================================================================
class ConfigManager:
    """
    SAFE configuration manager:
    - NEVER overrides existing user values
    - ONLY fills missing keys
    - NO automatic saving during load()
    """

    def __init__(self) -> None:
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self._lock = threading.RLock()
        self.data: Dict[str, Any] = {}

        self.load()

    # ------------------------------------------------------------------
    # Load config from disk
    # ------------------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            if self.config_file.exists():
                loaded = self._read_file()
                if loaded is None:
                    self.data = _default_config()
                else:
                    self.data = loaded
            else:
                self.data = _default_config()
                self._write_file(self.data)
                return

            # Only fill missing keys but do NOT override user values
            changed = self._merge_defaults(self.data, _default_config())

            # DO NOT save automatically unless defaults were missing
            if changed:
                self._write_file(self.data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config."""
        node = self.data
        for key in keys:
            if isinstance(node, Mapping) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, *keys: str, value: Any):
        """Set value and save to disk."""
        if not keys:
            raise ValueError("set() requires at least one key")

        with self._lock:
            # Validate platform
            if keys[0] == "platforms" and len(keys) == 2:
                subsystem = keys[1]
                allowed = SUPPORTED_PLATFORMS.get(subsystem)
                if allowed and value not in allowed:
                    raise ValueError(
                        f"Invalid platform '{value}' for '{subsystem}'. "
                        f"Allowed: {allowed}"
                    )

            # Traverse / create nested dicts
            node = self.data
            for key in keys[:-1]:
                if key not in node or not isinstance(node[key], MutableMapping):
                    node[key] = {}
                node = node[key]

            # Assign
            node[keys[-1]] = value

            # Save
            self._write_file(self.data)

    def get_api_key(self, platform_name: Optional[str]) -> Optional[str]:
        """
        Get API key based on selected platform.
        Uses new config structure: config.get(platform, "api_key")
        """
        if not platform_name:
            return None

        # Use new platform-specific config structure
        return self.get(platform_name, "api_key")

    def to_dict(self):
        with self._lock:
            return json.loads(json.dumps(self.data))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _read_file(self) -> Optional[Dict[str, Any]]:
        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _write_file(self, content: Dict[str, Any]):
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

    def _merge_defaults(self, current: MutableMapping[str, Any], default: Mapping[str, Any]) -> bool:
        """
        Only *adds missing keys*, never overwrites user config.
        Returns True if something was added.
        """
        changed = False

        for key, default_value in default.items():
            if key not in current:
                current[key] = default_value
                changed = True
            else:
                if isinstance(default_value, Mapping) and isinstance(current[key], MutableMapping):
                    if self._merge_defaults(current[key], default_value):
                        changed = True

        return changed


# Global instance
config = ConfigManager()

__all__ = [
    "config",
    "ConfigManager",
    "SUPPORTED_PLATFORMS",
    "CONFIG_DIR",
    "CONFIG_FILE",
]
