"""Lightweight command normalization utilities."""

from __future__ import annotations

import re
from typing import Optional


# Patterns for env var assignments at the start of a command: VAR=value
_ENV_ASSIGN_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+)+")
_MULTI_SPACE_RE = re.compile(r"\s+")


def normalize_command(command: str) -> str:
    """Return a normalized form of the command.

    - Strips leading/trailing whitespace
    - Collapses repeated internal whitespace
    - Strips leading environment variable assignments
    """
    cmd = command.strip()
    # Remove leading VAR=value assignments
    cmd = _ENV_ASSIGN_RE.sub("", cmd)
    # Collapse repeated whitespace
    cmd = _MULTI_SPACE_RE.sub(" ", cmd).strip()
    return cmd


def extract_verb(command: str) -> Optional[str]:
    """Extract the primary verb (first word) from a normalized command.

    Handles sudo transparently.
    """
    normalized = normalize_command(command)
    if not normalized:
        return None

    parts = normalized.split()
    if not parts:
        return None

    # Skip 'sudo', 'time', 'env', 'nohup', 'strace' prefixes
    skip = {"sudo", "time", "env", "nohup", "strace", "watch"}
    idx = 0
    while idx < len(parts) and parts[idx] in skip:
        idx += 1

    if idx >= len(parts):
        return parts[0] if parts else None

    verb = parts[idx]
    # Strip path components: /usr/bin/git -> git
    return verb.split("/")[-1] if "/" in verb else verb


def extract_features(command: str) -> dict:
    """Extract structural features from a command string.

    Returns a dict with boolean/string features useful for ranking and safety.
    """
    normalized = normalize_command(command)
    verb = extract_verb(command)

    has_pipe = "|" in command
    has_redirect_overwrite = bool(re.search(r"(?<![<>])>(?!>)", command))
    has_redirect_append = ">>" in command
    has_sudo = bool(re.search(r"(?:^|\s)sudo(?:\s|$)", command))
    has_wildcard = bool(re.search(r"[*?]", command))
    has_glob_curly = "{" in command and "}" in command

    return {
        "verb": verb,
        "normalized": normalized,
        "has_pipe": has_pipe,
        "has_redirect_overwrite": has_redirect_overwrite,
        "has_redirect_append": has_redirect_append,
        "has_sudo": has_sudo,
        "has_wildcard": has_wildcard,
        "has_glob_curly": has_glob_curly,
        "token_count": len(normalized.split()),
    }
