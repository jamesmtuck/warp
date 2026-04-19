"""Tests for doctor module."""
import pytest
from pathlib import Path
from unittest.mock import patch

from warp.doctor import run_doctor


def test_run_doctor_returns_int(tmp_path):
    config_path = tmp_path / "config.toml"
    from warp.config import default_config, save_config
    cfg = default_config()
    cfg.db_path = str(tmp_path / "warp.db")
    cfg.data_dir = str(tmp_path)
    save_config(cfg, config_path=config_path)

    from warp.db import init_db
    init_db(Path(cfg.db_path))

    with patch("warp.doctor.get_default_config_path", return_value=config_path):
        code = run_doctor(config_path=config_path)

    assert isinstance(code, int)
    assert code in (0, 1)


def test_run_doctor_missing_config(tmp_path):
    config_path = tmp_path / "nonexistent.toml"
    code = run_doctor(config_path=config_path)
    assert code == 1  # config not found -> fail
