"""Tests for retrieval module."""
import pytest
from pathlib import Path
from unittest.mock import patch

from warp.config import default_config
from warp.db import get_connection, init_db, insert_command
from warp.models import CaptureRecord
from warp.retrieval import (
    retrieve_recent_context,
    retrieve_repo_commands,
    retrieve_similar_commands,
    retrieve_successful_patterns,
)


def _insert_records(db: Path) -> None:
    records = [
        CaptureRecord(
            timestamp="2024-01-01T00:00:00Z",
            session_id="s1", shell="bash", cwd="/home/user",
            hostname="h", username="u",
            command_raw="git status", command_norm="git status",
            exit_code=0, success=1, verb="git", repo_root="/home/user/project",
        ),
        CaptureRecord(
            timestamp="2024-01-02T00:00:00Z",
            session_id="s1", shell="bash", cwd="/home/user",
            hostname="h", username="u",
            command_raw="find . -name '*.py'", command_norm="find . -name '*.py'",
            exit_code=0, success=1, verb="find", repo_root="/home/user/project",
        ),
        CaptureRecord(
            timestamp="2024-01-03T00:00:00Z",
            session_id="s1", shell="bash", cwd="/tmp",
            hostname="h", username="u",
            command_raw="ls /tmp", command_norm="ls /tmp",
            exit_code=0, success=1, verb="ls", repo_root=None,
        ),
    ]
    with get_connection(db) as conn:
        for r in records:
            insert_command(conn, r)


def test_retrieve_similar_commands(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    _insert_records(db)
    cfg = default_config()
    results = retrieve_similar_commands("git", db, cfg, limit=5)
    assert isinstance(results, list)
    assert any("git" in r.command_raw for r in results)


def test_retrieve_recent_context(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    _insert_records(db)
    results = retrieve_recent_context(db, limit=10)
    assert len(results) == 3


def test_retrieve_repo_commands(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    _insert_records(db)
    results = retrieve_repo_commands(db, "/home/user/project", limit=10)
    assert len(results) == 2
    assert all(r.repo_root == "/home/user/project" for r in results)


def test_retrieve_successful_patterns(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    _insert_records(db)
    cfg = default_config()
    results = retrieve_successful_patterns("find", db, cfg, limit=5)
    assert all(r.success == 1 for r in results)
