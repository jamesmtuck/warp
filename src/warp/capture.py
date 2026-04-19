"""Command capture logic for warp."""

from __future__ import annotations

import datetime
import re
import socket
import getpass
from pathlib import Path
from typing import Optional

from warp.config import WarpConfig
from warp.db import get_connection, get_last_command_in_session, insert_command
from warp.git_context import get_repo_root
from warp.models import CaptureRecord
from warp.normalize import extract_verb, normalize_command


def should_ignore_command(command: str, config: WarpConfig) -> bool:
    """Return True if the command should NOT be captured.

    Reasons to ignore:
    - blank/whitespace-only
    - starts with a space (if configured)
    - matches an ignored prefix
    - matches an ignored regex
    """
    if not command or not command.strip():
        return True

    if config.ignore_leading_space_commands and command.startswith(" "):
        return True

    stripped = command.strip()
    for prefix in config.ignored_prefixes:
        if stripped.startswith(prefix):
            return True

    for pattern in config.ignored_regexes:
        try:
            if re.search(pattern, stripped):
                return True
        except re.error:
            pass

    return False


def build_capture_record(
    command: str,
    exit_code: int,
    shell: str,
    cwd: str,
    session_id: str,
    duration_ms: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> CaptureRecord:
    """Build a CaptureRecord from raw shell hook data."""
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    repo_root = get_repo_root(cwd)
    norm = normalize_command(command)
    verb = extract_verb(command)
    success = 1 if exit_code == 0 else 0

    return CaptureRecord(
        timestamp=timestamp,
        session_id=session_id,
        shell=shell,
        cwd=cwd,
        repo_root=repo_root,
        hostname=socket.gethostname(),
        username=getpass.getuser(),
        command_raw=command.strip(),
        command_norm=norm,
        verb=verb,
        exit_code=exit_code,
        duration_ms=duration_ms,
        success=success,
    )


def capture_command(
    db_path: Path,
    config: WarpConfig,
    command: str,
    exit_code: int,
    shell: str,
    cwd: str,
    session_id: str,
    duration_ms: Optional[int] = None,
) -> bool:
    """Capture a command to the database.

    Returns True on success, False on any error (to never crash the shell).
    """
    try:
        if should_ignore_command(command, config):
            return False

        record = build_capture_record(
            command=command,
            exit_code=exit_code,
            shell=shell,
            cwd=cwd,
            session_id=session_id,
            duration_ms=duration_ms,
        )

        with get_connection(db_path) as conn:
            # Deduplicate: skip if same command in same session+cwd
            last = get_last_command_in_session(conn, session_id, cwd)
            if last and last["command_raw"] == record.command_raw:
                return False

            insert_command(conn, record)
        return True
    except Exception:
        # Never crash the shell
        return False
