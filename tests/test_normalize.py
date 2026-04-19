"""Tests for normalize module."""

import pytest
from warp.normalize import extract_features, extract_verb, normalize_command


def test_normalize_strips_whitespace():
    assert normalize_command("  ls -la  ") == "ls -la"


def test_normalize_collapses_spaces():
    assert normalize_command("ls   -la") == "ls -la"


def test_normalize_strips_env_vars():
    result = normalize_command("FOO=bar BAZ=qux ls -la")
    assert result == "ls -la"


def test_normalize_empty():
    assert normalize_command("") == ""
    assert normalize_command("   ") == ""


def test_extract_verb_simple():
    assert extract_verb("ls -la") == "ls"


def test_extract_verb_sudo():
    assert extract_verb("sudo apt-get install vim") == "apt-get"


def test_extract_verb_path():
    assert extract_verb("/usr/bin/git status") == "git"


def test_extract_verb_empty():
    assert extract_verb("") is None
    assert extract_verb("   ") is None


def test_extract_features_pipe():
    f = extract_features("cat file | grep foo")
    assert f["has_pipe"] is True
    assert f["has_redirect_overwrite"] is False


def test_extract_features_redirect():
    f = extract_features("echo hello > out.txt")
    assert f["has_redirect_overwrite"] is True
    assert f["has_redirect_append"] is False


def test_extract_features_append():
    f = extract_features("echo hello >> out.txt")
    assert f["has_redirect_append"] is True


def test_extract_features_sudo():
    f = extract_features("sudo rm -rf /tmp/junk")
    assert f["has_sudo"] is True


def test_extract_features_wildcard():
    f = extract_features("rm *.tmp")
    assert f["has_wildcard"] is True
