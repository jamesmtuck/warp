"""Infer soft preferences from command history."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from warp.models import SearchResult


_TOOL_ALTERNATIVES: list[tuple[str, str]] = [
    ("rg", "grep"),
    ("fd", "find"),
    ("bat", "cat"),
    ("exa", "ls"),
    ("delta", "diff"),
    ("procs", "ps"),
    ("dust", "du"),
    ("duf", "df"),
    ("hyperfine", "time"),
    ("zoxide", "cd"),
]

_PREVIEW_PATTERNS = [
    "find . -name",
    "find . -type",
    "-print",
    "--dry-run",
    "--preview",
]

_DESTRUCTIVE_PATTERNS = [
    "rm -rf",
    "rm -f",
    "rm ",
    "dd if=",
    "mkfs",
    "> /dev/",
]


def infer_tool_preferences(commands: list[SearchResult]) -> dict[str, str]:
    """Return preferred tool choices inferred from command history.

    Returns a dict like {'search': 'rg', 'find': 'fd'}.
    """
    verb_counts: Counter[str] = Counter()
    for cmd in commands:
        if cmd.verb:
            verb_counts[cmd.verb] += 1

    prefs: dict[str, str] = {}
    for modern, classic in _TOOL_ALTERNATIVES:
        modern_count = verb_counts.get(modern, 0)
        classic_count = verb_counts.get(classic, 0)
        if modern_count > 0:
            # User knows the modern tool; prefer it if used more
            if modern_count >= classic_count:
                prefs[classic] = modern
    return prefs


def infer_risk_preferences(commands: list[SearchResult]) -> dict[str, bool]:
    """Infer risk tolerance from command history."""
    preview_count = 0
    destructive_count = 0

    for cmd in commands:
        raw = cmd.command_raw.lower()
        if any(p in raw for p in _PREVIEW_PATTERNS):
            preview_count += 1
        if any(p in raw for p in _DESTRUCTIVE_PATTERNS):
            destructive_count += 1

    total = len(commands) or 1
    prefers_preview = preview_count > destructive_count
    has_destructive_history = destructive_count / total > 0.05

    return {
        "prefers_preview": prefers_preview,
        "has_destructive_history": has_destructive_history,
    }


def build_preference_summary(commands: list[SearchResult]) -> str:
    """Build a human-readable summary of inferred preferences."""
    tool_prefs = infer_tool_preferences(commands)
    risk_prefs = infer_risk_preferences(commands)

    parts: list[str] = []
    if tool_prefs:
        subs = ", ".join(f"prefer {v} over {k}" for k, v in tool_prefs.items())
        parts.append(f"Tool preferences: {subs}.")

    if risk_prefs.get("prefers_preview"):
        parts.append("User tends to preview before destructive operations.")
    if risk_prefs.get("has_destructive_history"):
        parts.append("User has some history of destructive commands.")

    return " ".join(parts) if parts else "No strong preferences inferred."
