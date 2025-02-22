"""Tests for configuration management."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict

import yaml

from dotfiles.core.config import Config


def test_default_config() -> None:
    """Test default configuration loading."""
    config = Config()
    assert config.search_paths == [
        str(Path("~/projects").expanduser()),
        str(Path("~/source").expanduser()),
    ]
    assert config.max_depth == 3
    assert "node_modules" in config.exclude_patterns
    assert ".venv" in config.exclude_patterns


def test_config_validation() -> None:
    """Test configuration validation."""
    config = Config()
    errors = config.validate()
    assert not errors, f"Default config should be valid, got errors: {errors}"


def create_temp_config(config_data: Dict) -> Path:
    """Create a temporary config file."""
    temp_file = NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    with temp_file:
        yaml.safe_dump(config_data, temp_file, encoding="utf-8")
    return Path(temp_file.name)


def test_load_config_file() -> None:
    """Test loading configuration from file."""
    test_config = {
        "search_paths": ["/test/path"],
        "max_depth": 5,
        "exclude_patterns": ["test_pattern"],
    }

    config_path = create_temp_config(test_config)
    try:
        config = Config()
        config.load_config(config_path)
        assert config.search_paths == ["/test/path"]
        assert config.max_depth == 5
        assert config.exclude_patterns == ["test_pattern"]
    finally:
        config_path.unlink()


def test_merge_config() -> None:
    """Test configuration merging."""
    config = Config()
    new_config = {
        "max_depth": 5,
        "programs": {
            "newprogram": {
                "name": "New Program",
                "files": [".newconfig"],
                "directories": [],
            }
        },
    }

    config._merge_config(new_config)
    assert config.max_depth == 5
    assert "newprogram" in config.programs
    assert config.get_program_config("cursor") is not None  # Original program still exists


def test_program_config() -> None:
    """Test program-specific configuration."""
    config = Config()
    cursor_config = config.get_program_config("cursor")
    assert cursor_config is not None
    assert cursor_config["name"] == "Cursor"
    assert ".cursorrules" in cursor_config["files"]
    assert ".cursor" in cursor_config["directories"]


def test_invalid_config() -> None:
    """Test handling of invalid configuration."""
    # This test is a placeholder for future validation testing
    # The invalid_config structure shows what we want to validate against
    # but we need to implement the validation logic first
    pass
