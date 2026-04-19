"""Tests for rule_backend module."""
import pytest
from warp.backends.rule_backend import RuleBackend


def test_find_files_request():
    backend = RuleBackend()
    result = backend.generate_candidates({
        "request": "find all .py files",
        "cwd": "/home/user",
        "shell": "bash",
    })
    assert "candidates" in result
    assert len(result["candidates"]) > 0
    cmds = [c["command"] for c in result["candidates"]]
    assert any("find" in c or ".py" in c for c in cmds)


def test_disk_usage_request():
    backend = RuleBackend()
    result = backend.generate_candidates({
        "request": "check disk space usage",
        "cwd": "/home/user",
        "shell": "bash",
    })
    candidates = result["candidates"]
    assert len(candidates) > 0
    cmds = [c["command"] for c in candidates]
    assert any("df" in c or "du" in c for c in cmds)


def test_git_status_request():
    backend = RuleBackend()
    result = backend.generate_candidates({
        "request": "show git status",
        "cwd": "/home/user/project",
        "shell": "bash",
    })
    candidates = result["candidates"]
    assert any("git" in c["command"] for c in candidates)


def test_explain_command():
    backend = RuleBackend()
    result = backend.explain_command({"command": "ls -la"})
    assert "explanation" in result
    assert "risk_level" in result


def test_log_files_request():
    backend = RuleBackend()
    result = backend.generate_candidates({
        "request": "find large log files modified this week",
        "cwd": "/home/user",
        "shell": "bash",
    })
    candidates = result["candidates"]
    assert len(candidates) > 0


def test_grep_request():
    backend = RuleBackend()
    result = backend.generate_candidates({
        "request": 'search for "error" in text files',
        "cwd": ".",
        "shell": "bash",
    })
    candidates = result["candidates"]
    assert len(candidates) > 0
    cmds = [c["command"] for c in candidates]
    assert any("grep" in c or "rg" in c for c in cmds)
