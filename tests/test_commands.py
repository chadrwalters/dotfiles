"""Test command functionality."""

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from dotfiles.cli import cli


@pytest.fixture
def cli_runner():
    """Create a CLI runner."""
    return CliRunner()


def test_backup_command(cli_runner, test_repo):
    """Test backup command."""
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Check backup was created
    backup_dir = Path("backups/test_repo")
    assert backup_dir.exists()
    assert any(backup_dir.glob("*/*"))

    # Cleanup
    shutil.rmtree("backups")


def test_backup_missing_dir(cli_runner):
    """Test backup with missing directory."""
    result = cli_runner.invoke(cli, ["backup", "nonexistent"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_restore_missing_backup(cli_runner, test_repo):
    """Test restore with missing backup directory."""
    result = cli_runner.invoke(cli, ["restore", "nonexistent", str(test_repo.path)])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_list_command(cli_runner, test_repo):
    """Test list command."""
    # First create a backup
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # List backups
    result = cli_runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "test_repo" in result.output
    assert "test" in result.output  # Program name

    # List specific repo
    result = cli_runner.invoke(cli, ["list", "test_repo"])
    assert result.exit_code == 0
    assert "test_repo" in result.output
    assert "test" in result.output

    # Cleanup
    shutil.rmtree("backups")
