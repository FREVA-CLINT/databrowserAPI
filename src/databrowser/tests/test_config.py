"""Unit tests for the configuration."""
import logging
from pathlib import Path
from typing import List

from databrowser.config import defaults, ServerConfig
from pytest import LogCaptureFixture


def test_valid_config() -> None:
    """Test the creation of a valid config file."""

    cfg = ServerConfig(defaults["API_CONFIG"], debug=True)
    assert cfg.log_level == 10
    assert cfg.solr_host == "localhost"
    defaults["DEBUG"] = False
    cfg.reload()
    assert cfg.solr_host == "localhost"


def test_invalid_config(caplog: LogCaptureFixture) -> None:
    """Test the behaviour for an invalid config file."""
    cfg = ServerConfig(Path("/foo/bar.toml"), debug=True)
    records: List[logging.LogRecord] = caplog.records
    assert any([record.levelname == "WARNING" for record in records])
    assert any(["Failed to load" in record.message for record in records])
