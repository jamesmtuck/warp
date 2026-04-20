"""Tests for the next-command prediction module."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from warp.config import WarpConfig
from warp.db import get_connection, init_db, insert_command
from warp.models import CaptureRecord
from warp.prediction import (
    PredictedCommand,
    _contextualize,
    _is_valid_sequence,
    predict_next_commands,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z"


def make_record(**kwargs) -> CaptureRecord:
    defaults = dict(
        timestamp=_ts(2024, 6, 1),
        session_id="sess1",
        shell="bash",
        cwd="/home/user",
        hostname="host",
        username="user",
        command_raw="ls",
        command_norm="ls",
        exit_code=0,
        success=1,
        repo_root=None,
        verb="ls",
        duration_ms=None,
    )
    defaults.update(kwargs)
    return CaptureRecord(**defaults)


def _populate_db(db: Path, records: list[dict]) -> None:
    init_db(db)
    with get_connection(db) as conn:
        for r in records:
            insert_command(conn, make_record(**r))


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestContextualize:
    def test_replaces_old_cwd(self):
        result = _contextualize("cat /old/dir/file.txt", "/old/dir", "/new/dir")
        assert result == "cat /new/dir/file.txt"

    def test_no_change_when_paths_equal(self):
        result = _contextualize("cat /same/dir/file.txt", "/same/dir", "/same/dir")
        assert result == "cat /same/dir/file.txt"

    def test_no_change_when_old_absent(self):
        result = _contextualize("echo hello", "/some/dir", "/other/dir")
        assert result == "echo hello"

    def test_no_change_when_old_cwd_empty(self):
        result = _contextualize("ls", "", "/new/dir")
        assert result == "ls"


class TestIsValidSequence:
    def test_same_named_session(self):
        assert _is_valid_sequence("sess1", "sess1", None, None) is True

    def test_unknown_session_not_valid_without_timestamps(self):
        assert _is_valid_sequence("unknown", "unknown", None, None) is False

    def test_different_sessions_with_close_timestamps(self):
        ts1 = _ts(2024, 6, 1, 10, 0)
        ts2 = _ts(2024, 6, 1, 10, 3)
        assert _is_valid_sequence("sessA", "sessB", ts1, ts2) is True

    def test_large_time_gap_is_invalid(self):
        ts1 = _ts(2024, 6, 1, 10, 0)
        ts2 = _ts(2024, 6, 1, 11, 30)  # 90 minutes apart
        assert _is_valid_sequence("unknown", "unknown", ts1, ts2) is False

    def test_exactly_at_boundary(self):
        ts1 = _ts(2024, 6, 1, 10, 0)
        ts2 = _ts(2024, 6, 1, 10, 10)  # exactly 600 seconds
        assert _is_valid_sequence("unknown", "unknown", ts1, ts2) is True


# ---------------------------------------------------------------------------
# Integration tests for predict_next_commands
# ---------------------------------------------------------------------------

class TestPredictNextCommandsEmpty:
    def test_empty_db_returns_empty(self, tmp_path):
        db = tmp_path / "w.db"
        init_db(db)
        cfg = WarpConfig()
        result = predict_next_commands(db_path=db, config=cfg, last_command="git status")
        assert result == []


class TestPredictTransitionSignal:
    """Sequence A → B should be predicted after A."""

    def _build_sequence(self, db: Path, session_id: str = "sess1") -> None:
        _populate_db(db, [
            dict(
                timestamp=_ts(2024, 6, 1, 10, 0),
                session_id=session_id,
                command_raw="git add .",
                command_norm="git add .",
                verb="git",
                cwd="/repo",
            ),
            dict(
                timestamp=_ts(2024, 6, 1, 10, 1),
                session_id=session_id,
                command_raw="git commit -m 'fix'",
                command_norm="git commit -m 'fix'",
                verb="git",
                cwd="/repo",
            ),
            dict(
                timestamp=_ts(2024, 6, 1, 10, 2),
                session_id=session_id,
                command_raw="git push",
                command_norm="git push",
                verb="git",
                cwd="/repo",
            ),
        ])

    def test_next_after_git_add(self, tmp_path):
        db = tmp_path / "w.db"
        self._build_sequence(db)
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db,
            config=cfg,
            last_command="git add .",
            cwd="/repo",
            limit=5,
        )
        assert predictions, "Expected at least one prediction"
        commands = [p.command for p in predictions]
        assert any("git commit" in c for c in commands), (
            f"Expected 'git commit' in predictions, got: {commands}"
        )

    def test_next_after_git_commit(self, tmp_path):
        db = tmp_path / "w.db"
        self._build_sequence(db)
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db,
            config=cfg,
            last_command="git commit -m 'fix'",
            cwd="/repo",
            limit=5,
        )
        commands = [p.command for p in predictions]
        assert any("git push" in c for c in commands), (
            f"Expected 'git push' in predictions, got: {commands}"
        )

    def test_last_command_excluded_from_predictions(self, tmp_path):
        db = tmp_path / "w.db"
        self._build_sequence(db)
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db,
            config=cfg,
            last_command="git add .",
            cwd="/repo",
        )
        for p in predictions:
            assert p.command != "git add ."

    def test_predictions_sorted_by_score_descending(self, tmp_path):
        db = tmp_path / "w.db"
        self._build_sequence(db)
        cfg = WarpConfig()
        predictions = predict_next_commands(db_path=db, config=cfg, last_command="git add .")
        scores = [p.score for p in predictions]
        assert scores == sorted(scores, reverse=True)

    def test_limit_respected(self, tmp_path):
        db = tmp_path / "w.db"
        self._build_sequence(db)
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db, config=cfg, last_command="git add .", limit=2
        )
        assert len(predictions) <= 2


class TestPredictContextFrequency:
    """Commands run often in the same CWD should surface even without a last_command."""

    def test_cwd_frequent_commands_returned(self, tmp_path):
        db = tmp_path / "w.db"
        _populate_db(db, [
            dict(
                timestamp=_ts(2024, 6, 1, 9, 0),
                session_id="s1",
                command_raw="pytest tests/",
                command_norm="pytest tests/",
                verb="pytest",
                cwd="/myproject",
            ),
            dict(
                timestamp=_ts(2024, 6, 1, 9, 30),
                session_id="s2",
                command_raw="pytest tests/",
                command_norm="pytest tests/",
                verb="pytest",
                cwd="/myproject",
            ),
        ])
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db, config=cfg, cwd="/myproject", limit=5
        )
        commands = [p.command for p in predictions]
        assert "pytest tests/" in commands

    def test_repo_frequent_commands_returned(self, tmp_path):
        db = tmp_path / "w.db"
        _populate_db(db, [
            dict(
                timestamp=_ts(2024, 6, 1, 9, 0),
                session_id="s1",
                command_raw="make build",
                command_norm="make build",
                verb="make",
                cwd="/project/src",
                repo_root="/project",
            ),
        ])
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db, config=cfg, cwd="/project/other", repo_root="/project", limit=5
        )
        commands = [p.command for p in predictions]
        assert "make build" in commands


class TestPredictContextualization:
    """Predicted commands should have old CWD substituted with current CWD."""

    def test_cwd_substituted_in_prediction(self, tmp_path):
        db = tmp_path / "w.db"
        _populate_db(db, [
            dict(
                timestamp=_ts(2024, 6, 1, 10, 0),
                session_id="s1",
                command_raw="cat /old/dir/config.yml",
                command_norm="cat /old/dir/config.yml",
                verb="cat",
                cwd="/old/dir",
            ),
            dict(
                timestamp=_ts(2024, 6, 1, 10, 1),
                session_id="s1",
                command_raw="vim /old/dir/config.yml",
                command_norm="vim /old/dir/config.yml",
                verb="vim",
                cwd="/old/dir",
            ),
        ])
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db,
            config=cfg,
            last_command="cat /old/dir/config.yml",
            cwd="/new/dir",
            limit=5,
        )
        commands = [p.command for p in predictions]
        # vim command should have old CWD replaced with new CWD
        assert any("/new/dir" in c for c in commands), (
            f"Expected /new/dir in a command, got: {commands}"
        )


class TestPredictReasons:
    """Predictions should include human-readable reasons."""

    def test_transition_reason_included(self, tmp_path):
        db = tmp_path / "w.db"
        _populate_db(db, [
            dict(
                timestamp=_ts(2024, 6, 1, 10, 0),
                session_id="s1",
                command_raw="npm install",
                command_norm="npm install",
                verb="npm",
                cwd="/app",
            ),
            dict(
                timestamp=_ts(2024, 6, 1, 10, 1),
                session_id="s1",
                command_raw="npm run build",
                command_norm="npm run build",
                verb="npm",
                cwd="/app",
            ),
        ])
        cfg = WarpConfig()
        predictions = predict_next_commands(
            db_path=db,
            config=cfg,
            last_command="npm install",
            cwd="/app",
            limit=5,
        )
        match = next((p for p in predictions if "npm run build" in p.command), None)
        assert match is not None
        assert match.reasons, "Expected non-empty reasons list"
