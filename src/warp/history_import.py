"""Import shell history into warp's database."""
from __future__ import annotations

import datetime
import os
import re
import socket
import getpass
from pathlib import Path
from typing import Optional

from warp.capture import should_ignore_command
from warp.config import WarpConfig
from warp.db import get_connection, insert_command
from warp.models import CaptureRecord
from warp.normalize import extract_verb, normalize_command


def _parse_zsh_history_line(line: str) -> Optional[str]:
    """Parse a zsh extended_history line or plain line.

    Extended format: ': timestamp:duration;command'
    Plain format: 'command'
    """
    # Extended format
    m = re.match(r"^: \d+:\d+;(.+)$", line)
    if m:
        return m.group(1)
    # Plain line
    stripped = line.strip()
    if stripped:
        return stripped
    return None


def _parse_bash_history_line(line: str) -> Optional[str]:
    """Parse a bash history line (plain text)."""
    stripped = line.strip()
    return stripped if stripped else None


def _detect_shell(history_file: Path) -> str:
    """Guess shell type from filename."""
    name = history_file.name.lower()
    if "zsh" in name:
        return "zsh"
    return "bash"


def import_shell_history(
    db_path: Path,
    config: WarpConfig,
    shell_type: Optional[str] = None,
    history_file: Optional[Path] = None,
    dry_run: bool = False,
) -> int:
    """Import commands from a shell history file.

    Returns the count of imported commands.
    """
    # Determine history file
    if history_file is None:
        home = Path.home()
        if shell_type == "zsh" or (shell_type is None and os.path.exists(home / ".zsh_history")):
            history_file = home / ".zsh_history"
            if shell_type is None:
                shell_type = "zsh"
        else:
            history_file = home / ".bash_history"
            if shell_type is None:
                shell_type = "bash"

    if not history_file.exists():
        return 0

    shell_type = shell_type or "bash"
    hostname = socket.gethostname()
    username = getpass.getuser()
    cwd = str(Path.home())
    session_id = "import"

    # Read lines
    try:
        with open(history_file, encoding="utf-8", errors="replace") as f:
            raw_lines = f.readlines()
    except OSError:
        return 0

    # Parse lines
    commands: list[str] = []
    for line in raw_lines:
        if shell_type == "zsh":
            cmd = _parse_zsh_history_line(line)
        else:
            cmd = _parse_bash_history_line(line)
        if cmd:
            commands.append(cmd)

    if dry_run:
        # Just count what would be imported
        valid = [c for c in commands if not should_ignore_command(c, config)]
        return len(valid)

    # Insert into DB
    count = 0
    seen: set[str] = set()
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    with get_connection(db_path) as conn:
        for cmd in commands:
            if should_ignore_command(cmd, config):
                continue
            if cmd in seen:
                continue
            seen.add(cmd)

            norm = normalize_command(cmd)
            verb = extract_verb(cmd)
            record = CaptureRecord(
                timestamp=timestamp,
                session_id=session_id,
                shell=shell_type,
                cwd=cwd,
                repo_root=None,
                hostname=hostname,
                username=username,
                command_raw=cmd,
                command_norm=norm,
                verb=verb,
                exit_code=0,
                duration_ms=None,
                success=1,
            )
            try:
                insert_command(conn, record)
                count += 1
            except Exception:
                continue

    return count
