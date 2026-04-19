"""Git context helpers for warp."""

from __future__ import annotations

import subprocess
from typing import Optional


def get_repo_root(cwd: str) -> Optional[str]:
    """Return the git repository root for the given cwd, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def is_git_repo(cwd: str) -> bool:
    """Return True if cwd is inside a git repository."""
    return get_repo_root(cwd) is not None


def get_git_branch(cwd: str) -> Optional[str]:
    """Return the current git branch name, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=3,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch != "HEAD" else None
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
