"""Tests for selectors module."""
import pytest
from unittest.mock import patch, MagicMock
from warp.selectors import has_fzf, select_from_items, select_with_builtin_menu


def test_has_fzf_when_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert has_fzf() is False


def test_has_fzf_when_installed():
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        assert has_fzf() is True


def test_select_with_builtin_menu_cancel(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "q")
    result = select_with_builtin_menu(["ls -la", "git status"])
    assert result is None


def test_select_with_builtin_menu_valid_selection(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "1")
    result = select_with_builtin_menu(["ls -la", "git status"])
    assert result == "ls -la"


def test_select_with_builtin_menu_out_of_range(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "99")
    result = select_with_builtin_menu(["ls -la"])
    assert result is None


def test_select_from_items_empty():
    result = select_from_items([])
    assert result is None


def test_select_from_items_builtin(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "2")
    with patch("warp.selectors.has_fzf", return_value=False):
        result = select_from_items(["cmd1", "cmd2"], selector="auto")
    assert result == "cmd2"
