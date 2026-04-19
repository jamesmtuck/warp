"""Tests for config module."""

import pytest
from pathlib import Path
import tempfile
import os

from warp.config import (
    WarpConfig,
    default_config,
    get_default_config_path,
    load_config,
    save_config,
)


def test_default_config_returns_instance():
    cfg = default_config()
    assert isinstance(cfg, WarpConfig)


def test_default_config_has_expected_fields():
    cfg = default_config()
    assert cfg.selector == "auto"
    assert cfg.model_backend == "rules"
    assert cfg.ignore_leading_space_commands is True
    assert cfg.history_retention_days > 0
    assert cfg.max_search_results > 0


def test_get_default_config_path_returns_path():
    p = get_default_config_path()
    assert isinstance(p, Path)
    assert p.name == "config.toml"


def test_save_and_load_config(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg = default_config()
    cfg.model_backend = "openai"
    cfg.max_search_results = 42

    save_config(cfg, config_path=cfg_path)
    assert cfg_path.exists()

    loaded = load_config(config_path=cfg_path)
    assert loaded.model_backend == "openai"
    assert loaded.max_search_results == 42


def test_load_config_missing_file_returns_defaults(tmp_path):
    missing = tmp_path / "no_such_file.toml"
    cfg = load_config(config_path=missing)
    assert isinstance(cfg, WarpConfig)
    assert cfg.model_backend == "rules"


def test_load_config_invalid_toml_returns_defaults(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("this is not: valid toml ::::")
    cfg = load_config(config_path=bad)
    assert isinstance(cfg, WarpConfig)
