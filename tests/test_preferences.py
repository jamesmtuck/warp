"""Tests for preferences module."""
import pytest
from warp.models import SearchResult
from warp.preferences import (
    build_preference_summary,
    infer_risk_preferences,
    infer_tool_preferences,
)


def _make_result(command_raw: str, verb: str) -> SearchResult:
    return SearchResult(
        id=1,
        command_raw=command_raw,
        command_norm=command_raw,
        cwd="/home/user",
        timestamp="2024-01-01T00:00:00Z",
        exit_code=0,
        success=1,
        verb=verb,
    )


def test_infer_tool_preferences_rg_over_grep():
    commands = [
        _make_result("rg pattern", "rg"),
        _make_result("rg other", "rg"),
        _make_result("grep thing .", "grep"),
    ]
    prefs = infer_tool_preferences(commands)
    assert prefs.get("grep") == "rg"


def test_infer_tool_preferences_no_modern_tool():
    commands = [_make_result("grep pattern .", "grep")]
    prefs = infer_tool_preferences(commands)
    assert "grep" not in prefs


def test_infer_risk_preferences_prefers_preview():
    commands = [
        _make_result("find . -name '*.log' -print", "find"),
        _make_result("find . -name '*.py' -print", "find"),
    ]
    prefs = infer_risk_preferences(commands)
    assert prefs["prefers_preview"] is True


def test_build_preference_summary_no_preferences():
    result = build_preference_summary([])
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_preference_summary_with_tools():
    commands = [_make_result("rg foo", "rg"), _make_result("rg bar", "rg")]
    result = build_preference_summary(commands)
    assert isinstance(result, str)
