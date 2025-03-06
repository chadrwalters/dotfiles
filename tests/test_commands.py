"""Test CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dotfiles.cli import cli
from dotfiles.core.repository import GitRepository


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a CLI runner."""
    return CliRunner()


@pytest.fixture
def test_repo(tmp_path: Path) -> GitRepository:
    """Create a test repository."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    # Create some files
    vscode_dir = repo_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text('{"foo": "bar"}')
    (vscode_dir / "extensions.json").write_text('{"extensions": []}')
    (repo_path / ".gitconfig").write_text("[user]\n\tname = Test User")
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/")
    cursor_dir = repo_path / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "settings.json").write_text('{"cursor": "settings"}')
    return GitRepository(repo_path)


def test_backup(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test backup command."""
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0
    assert "Backing up" in result.output


def test_backup_missing_dir(cli_runner: CliRunner) -> None:
    """Test backup command with missing directory."""
    result = cli_runner.invoke(cli, ["backup", "/path/does/not/exist"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_restore_missing_backup(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test restore command with missing backup."""
    result = cli_runner.invoke(cli, ["restore", "nonexistent", str(tmp_path)])
    assert result.exit_code == 1
    assert "No backups found" in result.output


def test_restore(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test restore command."""
    # First create a backup
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Then restore it
    result = cli_runner.invoke(cli, ["restore", test_repo.name, str(test_repo.path)])
    assert result.exit_code == 0
    # Check for either "Restored files" or "All files restored successfully" in the output
    assert any(
        msg in result.output for msg in ["Restored files", "All files restored successfully"]
    )


def test_list_command(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test list command."""
    # First create a backup
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Then list backups
    result = cli_runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    
    # Print the output for debugging
    print("\nTEST LIST OUTPUT:")
    print(result.output)
    
    # Verify the output has the expected columns - only check for basic columns that we know will be there
    assert "Repository" in result.output
    assert "Branch" in result.output
    assert "Backup Date" in result.output
    assert "Contents" in result.output
    
    # Verify the content of rows - check for the repo name which should be in the output
    assert test_repo.name in result.output
    
    # Test the --latest flag
    result = cli_runner.invoke(cli, ["list", "--latest"])
    assert result.exit_code == 0
    assert "Repository" in result.output
