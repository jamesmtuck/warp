"""Tests for capture module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from warp.capture import build_capture_record, capture_command, should_ignore_command
from warp.config import WarpConfig, default_config
from warp.db import get_connection, get_recent_commands, init_db


def test_should_ignore_blank():
    cfg = default_config()
    assert should_ignore_command("", cfg) is True
    assert should_ignore_command("   ", cfg) is True


def test_should_ignore_leading_space():
    cfg = default_config()
    cfg.ignore_leading_space_commands = True
    assert should_ignore_command(" secret_command", cfg) is True


def test_should_not_ignore_leading_space_when_disabled():
    cfg = default_config()
    cfg.ignore_leading_space_commands = False
    assert should_ignore_command(" secret_command", cfg) is False


def test_should_ignore_prefix():
    cfg = default_config()
    cfg.ignored_prefixes = ["warp ", "exit"]
    assert should_ignore_command("warp search foo", cfg) is True
    assert should_ignore_command("exit", cfg) is True


def test_should_not_ignore_normal_command():
    cfg = default_config()
    assert should_ignore_command("git status", cfg) is False


def test_should_ignore_regex():
    cfg = default_config()
    cfg.ignored_regexes = [r"^pass\w+"]
    assert should_ignore_command("password123", cfg) is True
    assert should_ignore_command("ls -la", cfg) is False


def test_build_capture_record_fields():
    with patch("warp.capture.get_repo_root", return_value=None):
        record = build_capture_record(
            command="git status",
            exit_code=0,
            shell="bash",
            cwd="/home/user/project",
            session_id="sess1",
            duration_ms=50,
        )
    assert record.command_raw == "git status"
    assert record.command_norm == "git status"
    assert record.verb == "git"
    assert record.exit_code == 0
    assert record.success == 1
    assert record.shell == "bash"
    assert record.cwd == "/home/user/project"


def test_capture_command_inserts_record(tmp_path):
    db = tmp_path / "test.db"
    from warp.db import init_db
    init_db(db)
    cfg = default_config()
    cfg.db_path = str(db)

    with patch("warp.capture.get_repo_root", return_value=None):
        result = capture_command(
            db_path=db,
            config=cfg,
            command="ls -la",
            exit_code=0,
            shell="bash",
            cwd="/tmp",
            session_id="sess1",
        )
    assert result is True

    with get_connection(db) as conn:
        rows = get_recent_commands(conn)
    assert len(rows) == 1
    assert rows[0]["command_raw"] == "ls -la"


def test_capture_command_deduplicates(tmp_path):
    db = tmp_path / "test.db"
    from warp.db import init_db
    init_db(db)
    cfg = default_config()

    with patch("warp.capture.get_repo_root", return_value=None):
        capture_command(db, cfg, "ls -la", 0, "bash", "/tmp", "sess1")
        result2 = capture_command(db, cfg, "ls -la", 0, "bash", "/tmp", "sess1")

    assert result2 is False  # Deduplicated

    with get_connection(db) as conn:
        rows = get_recent_commands(conn)
    assert len(rows) == 1


def test_capture_command_ignores_bad_command(tmp_path):
    db = tmp_path / "test.db"
    from warp.db import init_db
    init_db(db)
    cfg = default_config()

    result = capture_command(db, cfg, "", 0, "bash", "/tmp", "sess1")
    assert result is False
