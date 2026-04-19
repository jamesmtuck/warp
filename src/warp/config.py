"""Configuration management for warp."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tomllib
import tomli_w

from warp.constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_DATA_DIR,
    DEFAULT_DB_PATH,
    HISTORY_RETENTION_DAYS,
    IGNORED_PREFIXES,
    MAX_SEARCH_RESULTS,
)


@dataclass
class WarpConfig:
    """All configuration options for warp."""

    data_dir: str = str(DEFAULT_DATA_DIR)
    db_path: str = str(DEFAULT_DB_PATH)
    selector: str = "auto"  # auto / fzf / builtin
    model_backend: str = "rules"  # rules / openai / local
    ignored_prefixes: list[str] = field(default_factory=lambda: list(IGNORED_PREFIXES))
    ignored_regexes: list[str] = field(default_factory=list)
    ignore_leading_space_commands: bool = True
    history_retention_days: int = HISTORY_RETENTION_DAYS
    max_search_results: int = MAX_SEARCH_RESULTS
    prefer_preview_before_delete: bool = True
    preferred_search_tool: str = "auto"  # auto / rg / grep
    preferred_find_tool: str = "auto"  # auto / fd / find
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    local_llm_url: Optional[str] = None


def get_default_config_path() -> Path:
    """Return the default config file path (XDG-aware)."""
    return DEFAULT_CONFIG_PATH


def default_config() -> WarpConfig:
    """Return a default WarpConfig instance."""
    return WarpConfig()


def load_config(config_path: Optional[Path] = None) -> WarpConfig:
    """Load configuration from TOML file, falling back to defaults."""
    path = config_path or get_default_config_path()
    if not path.exists():
        return default_config()

    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except Exception:
        return default_config()

    cfg = default_config()
    for key, value in raw.get("warp", {}).items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)

    # Allow env var override for API key
    if not cfg.openai_api_key:
        cfg.openai_api_key = os.environ.get("OPENAI_API_KEY")

    return cfg


def save_config(cfg: WarpConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to a TOML file."""
    path = config_path or get_default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {"warp": {}}
    for key, value in cfg.__dict__.items():
        if value is not None:
            data["warp"][key] = value

    with open(path, "wb") as f:
        tomli_w.dump(data, f)
