from __future__ import annotations

from wiki2video.config.config_manager import config


def get_llm_timeout_seconds() -> int:
    value = config.get("global_config", "llm_timeout_seconds")
    try:
        return int(value) if value is not None else 120
    except (TypeError, ValueError):
        return 120


def get_llm_backoff_base() -> float:
    value = config.get("global_config", "llm_backoff_base")
    try:
        return float(value) if value is not None else 0.6
    except (TypeError, ValueError):
        return 0.6


def get_llm_backoff_max_tries() -> int:
    value = config.get("backoff_max_tries")
    try:
        return int(value) if value is not None else 5
    except (TypeError, ValueError):
        return 5


def get_llm_backoff_max_time() -> int:
    value = config.get("backoff_max_time")
    try:
        return int(value) if value is not None else 30
    except (TypeError, ValueError):
        return 30
