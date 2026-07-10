"""Tests for the configuration module."""

import importlib


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
