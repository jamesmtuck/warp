"""Deterministic rule-based backend for warp."""
from __future__ import annotations

import re
from typing import Any

from warp.backends.model_base import ModelBackend


def _candidate(command: str, explanation: str, assumptions: str = "", confidence: float = 0.85) -> dict:
    return {
        "command": command,
        "explanation": explanation,
        "assumptions": assumptions,
        "confidence": confidence,
        "risk_notes": "",
    }


def _find_files_response(request: str, cwd: str) -> list[dict]:
    """Generate find-file candidates."""
    candidates = []

    # Extension match
    ext_match = re.search(r"\.(\w+)\s+(?:files?|scripts?|sources?)", request, re.I)
    if ext_match:
        ext = ext_match.group(1)
        candidates.append(_candidate(
            f'find . -name "*.{ext}" -type f',
            f"Find all .{ext} files recursively from the current directory.",
            f"Assumes you want .{ext} files under current directory.",
        ))

    # Large files
    if re.search(r"large|big|huge|size|space", request, re.I):
        candidates.append(_candidate(
            "find . -type f -size +10M",
            "Find files larger than 10 MB.",
            "Assumes 10 MB threshold; adjust -size argument as needed.",
        ))

    # Recent/modified
    if re.search(r"recent|modified|changed|new|this week|today", request, re.I):
        candidates.append(_candidate(
            "find . -type f -mtime -7",
            "Find files modified in the last 7 days.",
            "Uses -mtime -7 for 7 days. Adjust as needed.",
        ))

    # Log files
    if re.search(r"log|\.log", request, re.I):
        candidates.append(_candidate(
            'find . -name "*.log" -type f',
            "Find all .log files.",
        ))
        if re.search(r"large|big|size", request, re.I):
            candidates.append(_candidate(
                'find . -name "*.log" -size +1M',
                "Find .log files larger than 1 MB.",
            ))

    # Fallback
    if not candidates:
        candidates.append(_candidate(
            "find . -type f",
            "Find all files recursively from the current directory.",
            "Generic file search. Refine with -name, -size, -mtime as needed.",
            confidence=0.6,
        ))

    return candidates[:3]


def _grep_response(request: str) -> list[dict]:
    """Generate grep/search candidates."""
    # Extract quoted pattern
    pattern_match = re.search(r'"([^"]+)"|\'([^\']+)\'|for\s+(\S+)', request, re.I)
    pattern = ""
    if pattern_match:
        pattern = pattern_match.group(1) or pattern_match.group(2) or pattern_match.group(3)

    if pattern:
        return [
            _candidate(
                f'grep -r "{pattern}" .',
                f'Search for "{pattern}" recursively in the current directory.',
                "Uses grep -r. Consider rg for speed.",
            ),
            _candidate(
                f'rg "{pattern}"',
                f'Fast recursive search for "{pattern}" using ripgrep.',
                "Requires ripgrep (rg) to be installed.",
                confidence=0.8,
            ),
        ]
    return [
        _candidate(
            'grep -r "PATTERN" .',
            "Recursive grep search. Replace PATTERN with your search term.",
            "Generic fallback.",
            confidence=0.5,
        )
    ]


def _disk_usage_response(request: str) -> list[dict]:
    """Generate disk usage candidates."""
    if re.search(r"largest|top|biggest|sort", request, re.I):
        return [
            _candidate(
                "du -sh * | sort -rh | head -20",
                "Show the top 20 largest items in the current directory, sorted by size.",
            ),
            _candidate(
                "df -h",
                "Show disk space usage for all mounted filesystems.",
            ),
        ]
    return [
        _candidate(
            "df -h",
            "Show disk space usage for all mounted filesystems in human-readable format.",
        ),
        _candidate(
            "du -sh .",
            "Show total disk usage of the current directory.",
        ),
    ]


def _process_response(request: str) -> list[dict]:
    """Generate process management candidates."""
    if re.search(r"memory|ram|mem", request, re.I):
        return [
            _candidate(
                "ps aux --sort=-%mem | head -20",
                "List the top 20 processes by memory usage.",
            ),
        ]
    if re.search(r"cpu|processor", request, re.I):
        return [
            _candidate(
                "ps aux --sort=-%cpu | head -20",
                "List the top 20 processes by CPU usage.",
            ),
        ]
    return [
        _candidate(
            "ps aux",
            "List all running processes.",
        ),
    ]


def _archive_response(request: str) -> list[dict]:
    """Generate archive/compression candidates."""
    if re.search(r"extract|unpack|untar|decompress", request, re.I):
        return [
            _candidate(
                "tar -xzf archive.tar.gz",
                "Extract a .tar.gz archive into the current directory.",
                "Replace archive.tar.gz with your filename.",
            ),
        ]
    if re.search(r"zip", request, re.I):
        return [
            _candidate(
                "zip -r archive.zip .",
                "Compress the current directory into a zip archive.",
            ),
        ]
    return [
        _candidate(
            "tar -czf archive.tar.gz .",
            "Create a gzip-compressed tar archive of the current directory.",
            "Replace . with the directory or files you want to archive.",
        ),
    ]


def _git_response(request: str) -> list[dict]:
    """Generate git candidates."""
    if re.search(r"status|changes|modified|staged", request, re.I):
        return [_candidate("git status", "Show the working tree status.")]
    if re.search(r"log|history|commit", request, re.I):
        return [
            _candidate(
                "git log --oneline -20",
                "Show the last 20 commits in compact form.",
            ),
            _candidate(
                "git log --graph --oneline --all",
                "Show a graph of all branches and commits.",
            ),
        ]
    if re.search(r"branch", request, re.I):
        return [
            _candidate("git branch -a", "List all local and remote branches."),
        ]
    if re.search(r"search|find|grep", request, re.I):
        return [
            _candidate(
                'git log --all --grep="PATTERN"',
                "Search commit messages for a pattern. Replace PATTERN.",
                "Replace PATTERN with your search term.",
                confidence=0.7,
            ),
        ]
    if re.search(r"stash", request, re.I):
        return [
            _candidate("git stash list", "List all stashes."),
        ]
    return [
        _candidate("git status", "Show git working tree status."),
    ]


def _todo_search_response(request: str) -> list[dict]:
    """Generate TODO/FIXME search candidates."""
    keyword = "TODO"
    if re.search(r"fixme", request, re.I):
        keyword = "FIXME"
    elif re.search(r"hack|xxx|note", request, re.I):
        keyword = "HACK"
    return [
        _candidate(
            f'grep -rn "{keyword}" . --include="*.py" --include="*.js" --include="*.ts"',
            f"Find all {keyword} comments in source files.",
        ),
        _candidate(
            f'rg "{keyword}"',
            f"Find all {keyword} comments using ripgrep (faster).",
            "Requires ripgrep.",
            confidence=0.8,
        ),
    ]


def _route_request(request: str, cwd: str) -> list[dict]:
    """Route a natural-language request to the appropriate handler."""
    req_lower = request.lower()

    if re.search(r"\bgrep\b|\bsearch\b.*text|\btext.*search|contains?\s", req_lower):
        return _grep_response(request)
    if re.search(r"\bfind\b.*\bfile|\bfile.*\bfind\b|search.*file|file.*search|locate.*file", req_lower):
        return _find_files_response(request, cwd)
    if re.search(r"\bdisk\b|\bspace\b|\bstorage\b|\bdu\b|\bdf\b", req_lower):
        return _disk_usage_response(request)
    if re.search(r"\bprocess\b|\bprocesses\b|\bcpu\b|\bmemory\b|\bkill\b|\bps\b", req_lower):
        return _process_response(request)
    if re.search(r"\barchive\b|\btar\b|\bzip\b|\bcompress\b|\bextract\b", req_lower):
        return _archive_response(request)
    if re.search(r"\bgit\b|\bcommit\b|\bbranch\b|\bstash\b", req_lower):
        return _git_response(request)
    if re.search(r"\btodo\b|\bfixme\b|\bhack\b", req_lower):
        return _todo_search_response(request)
    # Log files are common, try find fallback
    if re.search(r"\blog\b", req_lower):
        return _find_files_response(request, cwd)

    # Generic fallback
    return [
        _candidate(
            "# No deterministic rule matched your request.",
            "The rule backend could not match a pattern. Try the openai or local backend.",
            "",
            confidence=0.0,
        )
    ]


class RuleBackend(ModelBackend):
    """Deterministic rule-based model backend.

    Handles common command patterns without requiring an AI API.
    """

    def generate_candidates(self, context: dict) -> dict:
        """Generate command candidates using deterministic rules."""
        request = context.get("request", "")
        cwd = context.get("cwd", ".")
        candidates = _route_request(request, cwd)
        return {"candidates": candidates}

    def explain_command(self, context: dict) -> dict:
        """Explain a command using the explain module."""
        from warp.explain import explain_command
        command = context.get("command", "")
        result = explain_command(command)
        return {
            "explanation": result["explanation"],
            "warnings": result["warnings"],
            "risk_level": result["risk_level"],
            "safer_preview": result.get("safer_preview"),
        }
