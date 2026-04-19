"""Tests for ranking module."""

import pytest
from datetime import datetime, timezone

from warp.models import SearchResult
from warp.ranking import RankingContext, score_result


def make_result(**kwargs) -> SearchResult:
    defaults = dict(
        id=1,
        command_raw="ls -la",
        command_norm="ls -la",
        cwd="/home/user",
        timestamp="2024-01-01T00:00:00Z",
        exit_code=0,
        success=1,
        score=0.0,
        score_reasons=[],
        repo_root=None,
        verb="ls",
        session_id="sess1",
        shell="bash",
        hostname="host",
        username="user",
        duration_ms=None,
    )
    defaults.update(kwargs)
    return SearchResult(**defaults)


def test_score_exact_substring():
    ctx = RankingContext(query="ls -la")
    result = make_result(command_raw="ls -la /home")
    score, reasons = score_result(result, ctx)
    assert score > 0
    assert "exact_substring" in reasons


def test_score_same_cwd_bonus():
    ctx = RankingContext(query="git", cwd="/home/user/project")
    result = make_result(command_raw="git status", verb="git", cwd="/home/user/project")
    score_same, _ = score_result(result, ctx)

    result2 = make_result(command_raw="git status", verb="git", cwd="/other")
    score_diff, _ = score_result(result2, ctx)

    assert score_same > score_diff


def test_score_same_repo_bonus():
    ctx = RankingContext(query="git", repo_root="/home/user/project")
    result_same = make_result(command_raw="git log", verb="git", repo_root="/home/user/project")
    result_diff = make_result(command_raw="git log", verb="git", repo_root="/other")

    score_same, reasons_same = score_result(result_same, ctx)
    score_diff, _ = score_result(result_diff, ctx)

    assert score_same > score_diff
    assert "same_repo" in reasons_same


def test_score_success_bonus():
    ctx = RankingContext(query="ls")
    success = make_result(success=1)
    failure = make_result(success=0)

    s_succ, reasons = score_result(success, ctx)
    s_fail, _ = score_result(failure, ctx)

    assert s_succ > s_fail
    assert "success" in reasons


def test_recency_more_recent_scores_higher():
    now = datetime(2024, 6, 1, tzinfo=timezone.utc)
    ctx = RankingContext(query="ls", now=now)

    recent = make_result(timestamp="2024-05-31T00:00:00Z")
    old = make_result(timestamp="2023-01-01T00:00:00Z")

    score_recent, _ = score_result(recent, ctx)
    score_old, _ = score_result(old, ctx)

    assert score_recent > score_old
