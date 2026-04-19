"""Deterministic risk analysis for shell commands."""
from __future__ import annotations

import re
from typing import Optional


# Risk levels
RISK_LOW = "low"
RISK_MODERATE = "moderate"
RISK_HIGH = "high"


def _check_patterns(command: str) -> tuple[str, list[str], Optional[str]]:
    """Internal: check command against known risk patterns."""
    cmd = command.strip()
    warnings: list[str] = []
    risk = RISK_LOW
    safer: Optional[str] = None

    # ---- HIGH RISK ----
    # rm -rf (highest priority)
    if re.search(r"\brm\b.*-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r", cmd):
        risk = RISK_HIGH
        warnings.append("rm -rf can permanently delete files recursively with no recovery.")
        safer = re.sub(r"\brm\b", "echo rm", cmd, count=1)

    # dd (disk destroyer)
    elif re.search(r"(?:^|\s|\|)dd\s+", cmd):
        risk = RISK_HIGH
        warnings.append("dd can overwrite disk data irreversibly.")

    # mkfs (format filesystem)
    elif re.search(r"(?:^|\s)mkfs", cmd):
        risk = RISK_HIGH
        warnings.append("mkfs formats a filesystem, destroying all data on the target device.")

    # find -delete
    elif re.search(r"\bfind\b.*-delete\b", cmd):
        risk = RISK_HIGH
        warnings.append("find -delete permanently removes matching files.")
        safer = cmd.replace("-delete", "-print")

    # Wildcard rm
    elif re.search(r"\brm\b.*[*?]", cmd):
        risk = RISK_HIGH
        warnings.append("rm with wildcards can match and delete more files than expected.")
        # Suggest printf preview
        safer = re.sub(r"\brm\s+", "printf '%s\\n' ", cmd, count=1)

    # ---- MODERATE RISK ----
    elif re.search(r"(?:^|\s)rm\s", cmd):
        risk = RISK_MODERATE
        warnings.append("rm permanently deletes files.")
        safer = cmd.replace("rm ", "ls ", 1)

    elif re.search(r"\bmv\b.*[*?]|\bmv\b.*\s/", cmd):
        risk = RISK_MODERATE
        warnings.append("mv may overwrite destination files.")

    elif re.search(r"\bchmod\s+-R\b", cmd):
        risk = RISK_MODERATE
        warnings.append("chmod -R changes permissions recursively.")

    elif re.search(r"\bchown\s+-R\b", cmd):
        risk = RISK_MODERATE
        warnings.append("chown -R changes ownership recursively.")

    elif re.search(r"\bkill\s+-9\b", cmd):
        risk = RISK_MODERATE
        warnings.append("kill -9 forcibly terminates a process without cleanup.")

    elif re.search(r"(?<![<>])>(?!>)", cmd) and not re.search(r"\b(echo|printf)\b", cmd):
        # Shell overwrite redirect (not append) for non-trivial commands
        risk = RISK_MODERATE
        warnings.append("Shell redirect > will overwrite the target file.")
        safer = cmd.replace(">", ">>", 1) + "  # (changed to append; verify intent)"

    # sudo always at least moderate
    if re.search(r"(?:^|\s)sudo\s", cmd):
        if risk == RISK_LOW:
            risk = RISK_MODERATE
        warnings.insert(0, "Command runs with elevated privileges via sudo.")

    return risk, warnings, safer


def analyze_command_risk(
    command: str,
) -> tuple[str, list[str], Optional[str]]:
    """Analyze a shell command for risk.

    Returns:
        (risk_level, warnings, safer_preview_variant)
    """
    if not command or not command.strip():
        return RISK_LOW, [], None

    return _check_patterns(command)
