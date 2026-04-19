"""Environment and installation check for warp."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from warp.config import WarpConfig, get_default_config_path, load_config
from warp.constants import DEFAULT_DATA_DIR
from warp.selectors import has_fzf


_CHECK_OK = "  ✓"
_CHECK_FAIL = "  ✗"
_CHECK_WARN = "  !"


def _check_config(config_path: Path) -> tuple[bool, str]:
    if config_path.exists():
        return True, f"Config file found: {config_path}"
    return False, f"Config file not found: {config_path}  (run 'warp config init')"


def _check_db(db_path: Path) -> tuple[bool, str]:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Try a write test
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
        return True, f"Database writable: {db_path}"
    except Exception as e:
        return False, f"Database not writable: {db_path} ({e})"


def _check_shell_integration(data_dir: Path) -> tuple[bool, str]:
    """Check if shell integration files are present."""
    # Check for shell integration files in the installed package
    try:
        import importlib.resources as pkg_resources
        # Just check if the package has shell integration installed
        from warp import shell as _  # noqa
        return True, "Shell integration module available."
    except ImportError:
        pass

    # Check common locations
    for candidate in [
        Path(__file__).parent / "shell",
        data_dir / "shell",
    ]:
        if (candidate / "bash_integration.sh").exists():
            return True, f"Shell integration files found at {candidate}"

    return False, "Shell integration files not found. Check docs/install.md for setup instructions."


def _check_fzf() -> tuple[bool, str]:
    if has_fzf():
        return True, "fzf is installed (interactive selection available)."
    return False, "fzf not found. Install fzf for interactive selection (optional)."


def _check_git() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"git available: {version}"
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, "git not found. Git context features will be disabled."


def _check_backend(config: WarpConfig) -> tuple[bool, str]:
    backend = config.model_backend.lower()
    if backend == "rules":
        return True, "Backend: rules (no API key required)."
    if backend == "openai":
        has_key = bool(config.openai_api_key or os.environ.get("OPENAI_API_KEY"))
        if has_key:
            return True, "Backend: openai (API key configured)."
        return False, "Backend: openai, but no API key found. Set OPENAI_API_KEY or configure openai_api_key."
    if backend == "local":
        url = config.local_llm_url or "http://localhost:11434"
        return True, f"Backend: local LLM at {url} (not verified)."
    return False, f"Backend: unknown backend '{backend}'."


def run_doctor(config_path: Optional[Path] = None) -> int:
    """Run all doctor checks and print results.

    Returns 0 if all checks pass, 1 if any check fails.
    """
    config_path = config_path or get_default_config_path()
    config = load_config(config_path)
    db_path = Path(config.db_path)

    checks = [
        _check_config(config_path),
        _check_db(db_path),
        _check_shell_integration(Path(config.data_dir)),
        _check_fzf(),
        _check_git(),
        _check_backend(config),
    ]

    print("warp doctor\n")
    all_ok = True
    for ok, message in checks:
        prefix = _CHECK_OK if ok else _CHECK_FAIL
        print(f"{prefix}  {message}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("All checks passed.")
        return 0
    else:
        print("Some checks failed. See messages above.")
        return 1
