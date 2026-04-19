"""Utility helpers for warp."""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Optional


def get_os_platform() -> str:
    """Return a human-readable platform string."""
    system = platform.system().lower()
    if system == "darwin":
        return "macOS"
    if system == "linux":
        return "Linux"
    if system == "windows":
        return "Windows"
    return system or "unknown"


def get_shell() -> str:
    """Detect the current shell from environment variables."""
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        name = Path(shell_path).name.lower()
        if "zsh" in name:
            return "zsh"
        if "bash" in name:
            return "bash"
        if "fish" in name:
            return "fish"
        return name
    return "bash"


def truncate_list(items: list, max_items: int, label: str = "items") -> list:
    """Return first max_items, logging a warning if truncated."""
    if len(items) > max_items:
        return items[:max_items]
    return items


def format_candidate(candidate, index: int = 1, use_rich: bool = True) -> str:
    """Format a CandidateCommand for terminal display."""
    lines = [
        f"[{index}] {candidate.command}",
        f"    {candidate.explanation}",
    ]
    if candidate.assumptions:
        lines.append(f"    Assumptions: {candidate.assumptions}")
    if candidate.risk_level != "low":
        lines.append(f"    Risk: {candidate.risk_level.upper()}")
    for w in candidate.risk_warnings:
        lines.append(f"    ⚠  {w}")
    if candidate.safer_preview:
        lines.append(f"    Safer preview: {candidate.safer_preview}")
    return "\n".join(lines)


def print_candidates(candidates: list, title: str = "Candidate commands:") -> None:
    """Print a list of CandidateCommand objects to stdout."""
    print(title)
    for i, c in enumerate(candidates, 1):
        print(format_candidate(c, index=i))
        print()


def ensure_dir(path: Path) -> None:
    """Create a directory and all parents if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
