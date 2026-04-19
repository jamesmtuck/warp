"""Tests for db module."""

import pytest
from pathlib import Path

from warp.db import (
    fts_search,
    get_connection,
    get_recent_commands,
    init_db,
    insert_command,
    row_to_search_result,
)
from warp.models import CaptureRecord


def make_record(**kwargs) -> CaptureRecord:
    defaults = dict(
        timestamp="2024-01-01T00:00:00Z",
        session_id="sess1",
        shell="bash",
        cwd="/home/user",
        hostname="host1",
        username="user",
        command_raw="ls -la",
        command_norm="ls -la",
        exit_code=0,
        success=1,
        repo_root=None,
        verb="ls",
        duration_ms=10,
    )
    defaults.update(kwargs)
    return CaptureRecord(**defaults)


def test_init_db_creates_file(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    assert db.exists()


def test_insert_and_retrieve(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    record = make_record(command_raw="git status", command_norm="git status", verb="git")
    with get_connection(db) as conn:
        row_id = insert_command(conn, record)
        assert row_id > 0
        rows = get_recent_commands(conn)
        assert len(rows) == 1
        assert rows[0]["command_raw"] == "git status"


def test_fts_search(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_command(conn, make_record(command_raw="find . -name '*.log'", command_norm="find . -name '*.log'", verb="find"))
        insert_command(conn, make_record(command_raw="ls -la /tmp", command_norm="ls -la /tmp", verb="ls"))

    with get_connection(db) as conn:
        results = fts_search(conn, "find", limit=10)
        assert len(results) >= 1
        cmds = [r["command_raw"] for r in results]
        assert any("find" in c for c in cmds)


def test_row_to_search_result(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_command(conn, make_record())
        rows = get_recent_commands(conn)
        sr = row_to_search_result(rows[0])
    assert sr.command_raw == "ls -la"
    assert sr.exit_code == 0
    assert sr.success == 1


def test_get_recent_commands_by_cwd(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_command(conn, make_record(cwd="/home/user", command_raw="ls"))
        insert_command(conn, make_record(cwd="/tmp", command_raw="pwd"))
        rows = get_recent_commands(conn, cwd="/tmp")
        assert len(rows) == 1
        assert rows[0]["command_raw"] == "pwd"
