"""Tests for explain module."""
import pytest
from warp.explain import explain_command


def test_explain_ls():
    result = explain_command("ls -la")
    assert result["verb"] == "ls"
    assert "list" in result["explanation"].lower() or "ls" in result["explanation"].lower()
    assert result["risk_level"] == "low"
    assert result["warnings"] == []


def test_explain_rm_rf():
    result = explain_command("rm -rf /tmp/junk")
    assert result["verb"] == "rm"
    assert result["risk_level"] == "high"
    assert len(result["warnings"]) > 0


def test_explain_git():
    result = explain_command("git status")
    assert result["verb"] == "git"
    assert "git" in result["explanation"].lower() or "version" in result["explanation"].lower()


def test_explain_pipeline():
    result = explain_command("cat file.txt | grep error")
    assert result["has_pipeline"] is True


def test_explain_redirect():
    result = explain_command("echo hello > out.txt")
    assert result["has_redirect"] is True


def test_explain_unknown_verb():
    result = explain_command("mymysteriouscommand --flag")
    assert result["verb"] == "mymysteriouscommand"
    assert result["explanation"] is not None


def test_explain_empty():
    result = explain_command("")
    assert result["explanation"] == "Empty command."
    assert result["verb"] is None
