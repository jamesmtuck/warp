"""Tests for search module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from warp.config import default_config
from warp.db import get_connection, init_db, insert_command
from warp.models import CaptureRecord
from warp.search import search_history


def insert_test_records(db: Path) -> None:
    records = [
        CaptureRecord(
            timestamp="2024-01-01T00:00:00Z",
            session_id="s1",
            shell="bash",
            cwd="/home/user",
            hostname="h",
            username="u",
            command_raw="find . -name '*.log'",
            command_norm="find . -name '*.log'",
            exit_code=0,
            success=1,
            verb="find",
        ),
        CaptureRecord(
            timestamp="2024-01-02T00:00:00Z",
            session_id="s1",
            shell="bash",
            cwd="/home/user",
            hostname="h",
            username="u",
            command_raw="ls -la /var/log",
            command_norm="ls -la /var/log",
            exit_code=0,
            success=1,
            verb="ls",
        ),
        CaptureRecord(
            timestamp="2024-01-03T00:00:00Z",
            session_id="s1",
            shell="bash",
            cwd="/home/user",
            hostname="h",
            username="u",
            command_raw="grep -r error /var/log",
            command_norm="grep -r error /var/log",
            exit_code=0,
            success=1,
            verb="grep",
        ),
    ]
    with get_connection(db) as conn:
        for r in records:
            insert_command(conn, r)


def test_search_history_basic(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    insert_test_records(db)

    cfg = default_config()
    results = search_history("find", db, cfg)
    assert len(results) > 0
    cmds = [r.command_raw for r in results]
    assert any("find" in c for c in cmds)


def test_search_history_limits_results(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    insert_test_records(db)

    cfg = default_config()
    results = search_history("log", db, cfg, limit=2)
    assert len(results) <= 2


def test_search_history_empty_db(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    cfg = default_config()
    results = search_history("anything", db, cfg)
    assert results == []
