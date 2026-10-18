"""Tests for model selection and version metadata in vista.config."""

import importlib

import pytest

from vista import config


@pytest.fixture
def reload_config(monkeypatch):
    for var in ("VISTA_MODEL", "FOLLOWUPS_MODEL", "VISTA_PREMIUM_MODEL"):
        monkeypatch.delenv(var, raising=False)

    def _reload():
        return importlib.reload(config)

    yield _reload
    monkeypatch.undo()
    importlib.reload(config)


def test_default_models_are_current(reload_config):
    cfg = reload_config()
    assert cfg.DEFAULT_MODEL == "claude-sonnet-5-5"
    assert cfg.PREMIUM_MODEL == "claude-fable-5-1"


def test_vista_model_env_overrides_default(reload_config, monkeypatch):
    monkeypatch.setenv("VISTA_MODEL", "claude-opus-5-5")
    assert reload_config().DEFAULT_MODEL == "claude-opus-5-5"


def test_legacy_followups_model_env_still_honored(reload_config, monkeypatch):
    monkeypatch.setenv("FOLLOWUPS_MODEL", "claude-haiku-5-5")
    assert reload_config().DEFAULT_MODEL == "claude-haiku-5-5"


def test_vista_model_wins_over_legacy_name(reload_config, monkeypatch):
    monkeypatch.setenv("FOLLOWUPS_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("VISTA_MODEL", "claude-opus-5-5")
    assert reload_config().DEFAULT_MODEL == "claude-opus-5-5"


def test_premium_model_env_override(reload_config, monkeypatch):
    monkeypatch.setenv("VISTA_PREMIUM_MODEL", "claude-opus-5-5")
    assert reload_config().PREMIUM_MODEL == "claude-opus-5-5"


def test_version_comes_from_package_metadata():
    from importlib.metadata import version

    assert config.VERSION == version("vista")
    assert config.USER_AGENT.startswith(f"vista/{config.VERSION} ")
