"""Tests for the configuration module."""

import importlib
from pathlib import Path


def test_config_import():
    """The config module can be imported."""
    import config

    assert config is not None


def test_data_root_resolved_from_env(tmp_path, monkeypatch):
    """DATA_DIR drives the resolved data-directory layout."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    import config

    importlib.reload(config)

    assert config.DATA_ROOT is not None
    assert config.DATABASE_DIR == config.DATA_ROOT / "database"
    assert config.STORAGE_DIR == config.DATA_ROOT / "storage"
    assert config.DATA_FILE == config.DATABASE_DIR / "data.json"


def test_save_data_path_refuses_root_home_and_system_dirs(tmp_path, monkeypatch):
    """/api/file serves the whole data directory, so it may not be / , ~ or a system dir."""
    import config

    monkeypatch.setattr(config, "SETTINGS_DIR", tmp_path / "settings")
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings" / "settings.json")
    for forbidden in ("/", str(Path.home()), "/etc"):
        assert config.save_data_path(forbidden) is False
    assert not config.SETTINGS_FILE.exists()

    ok = tmp_path / "receipts-data"
    assert config.save_data_path(str(ok)) is True
