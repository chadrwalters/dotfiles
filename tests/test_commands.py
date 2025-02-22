"""Tests for CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from dotfiles.core.backup import BackupManager
from dotfiles.core.bootstrap import BootstrapManager
from dotfiles.core.commands import (
    backup,
    bootstrap,
    list_backups,
    list_repos,
    restore,
    wipe,
)
from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository
from dotfiles.core.restore import RestoreManager


@pytest.fixture
def args() -> argparse.Namespace:
    """Create test command arguments."""
    args = argparse.Namespace()
    # Common arguments
    args.repo = None  # Repository name, None means all repos
    args.program = None  # Program name, None means all programs
    args.branch = None  # Branch name, None means current branch
    args.dry_run = False  # Whether to perform a dry run
    args.force = False  # Whether to force operations
    args.template = None  # Template name for bootstrap
    return args


def test_list_repos_empty(
    args: argparse.Namespace, test_config: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test listing repositories when none exist."""
    test_config._merge_config(
        {
            "search_paths": ["/nonexistent/path"],
        }
    )

    assert list_repos(args, test_config) == 0
    captured = capsys.readouterr()
    assert "No repositories found" in captured.out


def test_list_repos(
    args: argparse.Namespace,
    test_config: Config,
    temp_workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test listing repositories."""
    # Update config to include test workspace
    test_config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_workspace)
        assert list_repos(args, test_config) == 0
        captured = capsys.readouterr()
        assert "repo1" in captured.out
        assert "repo2" in captured.out
        assert "repo3" in captured.out
        assert "not_a_repo" not in captured.out


def test_list_backups_empty(
    args: argparse.Namespace,
    test_config: Config,
    temp_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test listing backups when none exist."""
    args.repo = None
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert list_backups(args, test_config) == 0
        captured = capsys.readouterr()
        assert "No backups found" in captured.out


def test_list_backups_all(
    args: argparse.Namespace,
    test_config: Config,
    temp_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test listing all backups."""
    args.repo = None
    # Create test backup structure
    backup_dir = temp_dir / "backups" / "testrepo" / "main" / "20240101-000000"
    backup_dir.mkdir(parents=True)
    (backup_dir / "cursor").mkdir()
    (backup_dir / "vscode").mkdir()

    # Create another repo backup
    backup_dir2 = temp_dir / "backups" / "testrepo2" / "main" / "20240101-000000"
    backup_dir2.mkdir(parents=True)
    (backup_dir2 / "cursor").mkdir()

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert list_backups(args, test_config) == 0
        captured = capsys.readouterr()
        assert "testrepo" in captured.out
        assert "testrepo2" in captured.out


def test_list_backups_filtered(
    args: argparse.Namespace,
    test_config: Config,
    temp_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test listing backups filtered by repository."""
    args.repo = "testrepo"
    # Create test backup structure
    backup_dir = temp_dir / "backups" / "testrepo" / "main" / "20240101-000000"
    backup_dir.mkdir(parents=True)
    (backup_dir / "cursor").mkdir()
    (backup_dir / "vscode").mkdir()

    # Create another repo backup that shouldn't be shown
    backup_dir2 = temp_dir / "backups" / "testrepo2" / "main" / "20240101-000000"
    backup_dir2.mkdir(parents=True)
    (backup_dir2 / "cursor").mkdir()

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert list_backups(args, test_config) == 0
        captured = capsys.readouterr()
        assert "testrepo" in captured.out
        assert "testrepo2" not in captured.out


def test_backup_not_implemented(
    args: argparse.Namespace,
    test_config: Config,
    temp_git_repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test backup command."""
    args.repo = temp_git_repo.name
    # Create test files
    (temp_git_repo / ".cursorrules").write_text("test")
    (temp_git_repo / ".cursor").mkdir()
    (temp_git_repo / ".cursor" / "rules").mkdir(parents=True)
    (temp_git_repo / ".cursor" / "rules" / "test.mdc").write_text("test")

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_git_repo.parent)
        test_config._merge_config(
            {
                "search_paths": [str(temp_git_repo.parent)],
                "programs": {
                    "cursor": {
                        "name": "Cursor",
                        "paths": [".cursorrules", ".cursor/rules/*.mdc", ".cursor/"],
                        "files": [".cursorrules", ".cursor/rules/*.mdc"],
                        "directories": [".cursor"],
                    }
                },
            }
        )
        assert backup(args, test_config) == 0


def test_restore(
    restore_manager: RestoreManager,
    backup_manager: BackupManager,
    temp_git_repo: Path,
    test_config: Config,
) -> None:
    """Test restore command."""
    repo = GitRepository(temp_git_repo)

    # Create test files first
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "rules").mkdir()
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = temp_git_repo / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (temp_git_repo / ".gitconfig").write_text("[user]\n\tname = Test User")
    (temp_git_repo / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Create a backup first
    backup_manager.backup(repo)

    # Modify a file to test restore
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("modified content")

    args = argparse.Namespace(
        repo=str(temp_git_repo),
        program=None,
        branch=None,
        dry_run=False,
        force=True,
        backup_dir=str(backup_manager.backup_dir),
    )

    result = restore(args, test_config)
    assert result == 0


def test_bootstrap(
    bootstrap_manager: BootstrapManager,
    backup_manager: BackupManager,
    temp_git_repo: Path,
    test_config: Config,
) -> None:
    """Test bootstrap command."""
    repo = GitRepository(temp_git_repo)

    # Create test files first
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "rules").mkdir()
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = temp_git_repo / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (temp_git_repo / ".gitconfig").write_text("[user]\n\tname = Test User")
    (temp_git_repo / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Create a backup to use as template
    backup_manager.backup(repo)

    # Get the backup path
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    template_path = backups[0]

    # Create a new repo
    new_repo = temp_git_repo.parent / "new_repo"
    new_repo.mkdir()

    args = argparse.Namespace(
        repo=str(new_repo),
        program=None,
        branch=None,
        template=str(template_path),
        dry_run=False,
        force=False,
        backup_dir=str(backup_manager.backup_dir),
    )

    result = bootstrap(args, test_config)
    assert result == 0
    assert (new_repo / "test.txt").exists()
    assert (new_repo / "test.txt").read_text() == "test content"


def test_bootstrap_no_template(bootstrap_manager: BootstrapManager, test_config: Config) -> None:
    """Test bootstrap command with no template."""
    args = argparse.Namespace(
        repo="new_repo", program=None, branch=None, template=None, dry_run=False, force=False
    )

    result = bootstrap(args, test_config)
    assert result == 1  # Should fail when no template is available


def test_wipe_not_implemented(
    args: argparse.Namespace,
    test_config: Config,
    temp_git_repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test wipe command."""
    args.repo = temp_git_repo.name
    # Create test files
    (temp_git_repo / ".cursorrules").write_text("test")
    (temp_git_repo / ".cursor").mkdir()
    (temp_git_repo / ".cursor" / "rules").mkdir(parents=True)
    (temp_git_repo / ".cursor" / "rules" / "test.mdc").write_text("test")

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_git_repo.parent)
        test_config._merge_config(
            {
                "search_paths": [str(temp_git_repo.parent)],
                "programs": {
                    "cursor": {
                        "name": "Cursor",
                        "paths": [".cursorrules", ".cursor/rules/*.mdc", ".cursor/"],
                        "files": [".cursorrules", ".cursor/rules/*.mdc"],
                        "directories": [".cursor"],
                    }
                },
            }
        )
        assert wipe(args, test_config) == 0
