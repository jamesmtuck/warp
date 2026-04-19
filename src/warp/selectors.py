"""Interactive selection UI for warp."""
from __future__ import annotations

import subprocess
import sys
from typing import Optional


def has_fzf() -> bool:
    """Return True if fzf is installed and available."""
    try:
        result = subprocess.run(
            ["fzf", "--version"],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def select_with_fzf(items: list[str], prompt: str = "Select> ") -> Optional[str]:
    """Present items through fzf for interactive selection.

    Returns the selected item, or None if cancelled.
    """
    try:
        proc = subprocess.run(
            ["fzf", "--prompt", prompt, "--height", "40%", "--reverse"],
            input="\n".join(items),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.strip()
    except (OSError, FileNotFoundError):
        pass
    return None


def select_with_builtin_menu(
    items: list[str],
    prompt: str = "Select a command (number, or q to cancel): ",
) -> Optional[str]:
    """Present a numbered text menu for interactive selection.

    Returns the selected item, or None if cancelled.
    """
    if not items:
        return None
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    print()
    try:
        raw = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if raw.lower() in ("q", "quit", "cancel", ""):
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(items):
            return items[idx]
    except ValueError:
        pass
    return None


def select_from_items(
    items: list[str],
    prompt: str = "Select> ",
    selector: str = "auto",
) -> Optional[str]:
    """Select an item from a list using the configured selector.

    Args:
        items: List of string items to choose from.
        prompt: Prompt text for the selector.
        selector: 'auto', 'fzf', or 'builtin'.

    Returns the selected item, or None.
    """
    if not items:
        return None

    use_fzf = (selector == "fzf") or (selector == "auto" and has_fzf())

    if use_fzf:
        result = select_with_fzf(items, prompt=prompt)
        if result is not None:
            return result
        # Fall back to builtin if fzf fails
    return select_with_builtin_menu(items, prompt=prompt)
