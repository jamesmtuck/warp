"""Project-wide constants."""

import os
from pathlib import Path

APP_NAME = "warp"
DEFAULT_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
DEFAULT_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "warp.db"

DB_WAL_TIMEOUT = 30  # seconds
MAX_SEARCH_RESULTS = 20
HISTORY_RETENTION_DAYS = 365

IGNORED_PREFIXES: list[str] = [
    "warp ",
    "exit",
    "logout",
    "clear",
    "reset",
]

SHELL_BASH = "bash"
SHELL_ZSH = "zsh"
SUPPORTED_SHELLS = [SHELL_BASH, SHELL_ZSH]
