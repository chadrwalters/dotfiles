"""Tests for restore functionality."""

import shutil
from pathlib import Path
from typing import Generator

import pytest

from dotfiles.core.backup import BackupManager
from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository
from dotfiles.core.restore import RestoreManager
from tests.test_backup import create_test_files


@pytest.fixture
def restore_manager(
    test_config: Config, backup_manager: BackupManager, backup_dir: Path
) -> RestoreManager:
    """Create a restore manager with test configuration."""
    manager = RestoreManager(test_config, backup_manager)
    return manager


@pytest.fixture(autouse=True)
def clean_test_files(temp_git_repo: Path) -> Generator[None, None, None]:
    """Clean up test files before and after each test."""
    # Clean up any existing test files
    test_files = [
        ".cursor",
        ".vscode",
        ".gitconfig",
        ".gitignore",
    ]
    for test_file in test_files:
        test_path = temp_git_repo / test_file
        if test_path.exists():
            if test_path.is_dir():
                shutil.rmtree(test_path)
            else:
                test_path.unlink()

    # Clean up any existing backups
    backup_dir = Path("test_temp/backups")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    yield

    # Clean up after test
    for test_file in test_files:
        test_path = temp_git_repo / test_file
        if test_path.exists():
            if test_path.is_dir():
                shutil.rmtree(test_path)
            else:
                test_path.unlink()

    # Clean up backups again
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


@pytest.fixture
def backup_with_files(backup_manager: BackupManager, temp_git_repo: Path) -> Path:
    """Create a backup with test files."""
    # Clean up any existing backups
    backup_dir = backup_manager.backup_dir / "git_repo"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    # Create test files
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    (cursor_dir / "rules").mkdir(exist_ok=True)
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = temp_git_repo / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (temp_git_repo / ".gitconfig").write_text("[user]\n\tname = Test User")
    (temp_git_repo / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Create backup
    repo = GitRepository(temp_git_repo)
    backup_manager.backup(repo)

    # Get the backup path
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    backup_path = backups[0]
    assert isinstance(backup_path, Path)
    return backup_path


def test_find_backup_empty(restore_manager: RestoreManager) -> None:
    """Test finding backup when none exist."""
    assert restore_manager.find_backup("nonexistent") is None


def test_find_backup(restore_manager: RestoreManager, backup_with_files: Path) -> None:
    """Test finding backup."""
    repo_name = backup_with_files.parent.parent.name
    backup = restore_manager.find_backup(repo_name)
    assert backup == backup_with_files


def test_find_backup_with_branch(restore_manager: RestoreManager, backup_with_files: Path) -> None:
    """Test finding backup with branch."""
    repo_name = backup_with_files.parent.parent.name
    branch_name = backup_with_files.parent.name
    backup = restore_manager.find_backup(repo_name, branch=branch_name)
    assert backup == backup_with_files


def test_check_conflicts_empty(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test checking conflicts when none exist."""
    repo = GitRepository(temp_git_repo)

    # Clean up any existing files
    for path in [".cursor", ".vscode", ".gitconfig", ".gitignore"]:
        full_path = temp_git_repo / path
        if full_path.is_dir():
            shutil.rmtree(full_path)
        elif full_path.exists():
            full_path.unlink()

    conflicts = restore_manager.check_conflicts(repo, backup_with_files)
    assert not conflicts, "Expected no conflicts in empty repository"


def test_check_conflicts(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test checking conflicts."""
    # Create conflicting files
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    conflicts = restore_manager.check_conflicts(repo, backup_with_files)
    assert conflicts
    assert any(".cursorrules" in str(p[1]) for p in conflicts)
    assert any(".cursor" in str(p[1]) for p in conflicts)


def test_restore_conflicts(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test restore with conflicts."""
    repo = GitRepository(temp_git_repo)

    # Create conflicting files
    (temp_git_repo / ".cursor" / ".cursorrules").write_text("conflict")
    (temp_git_repo / ".vscode" / "settings.json").write_text("conflict")

    # Attempt restore without force
    # With the new behavior, restore returns True if files were skipped
    result = restore_manager.restore(repo.name, temp_git_repo)
    assert result

    # Verify files were not overwritten
    assert (temp_git_repo / ".cursor" / ".cursorrules").read_text() == "conflict"
    assert (temp_git_repo / ".vscode" / "settings.json").read_text() == "conflict"

    # Now restore with force
    result = restore_manager.restore(repo.name, temp_git_repo, force=True)
    assert result

    # Verify files were overwritten
    assert (temp_git_repo / ".cursor" / ".cursorrules").read_text() != "conflict"
    assert (temp_git_repo / ".vscode" / "settings.json").read_text() != "conflict"


def test_restore_all_programs(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test restoring all programs."""
    repo = GitRepository(temp_git_repo)

    # Restore all programs with force
    assert restore_manager.restore(repo.name, temp_git_repo, force=True)

    # Verify all files were restored
    assert (temp_git_repo / ".cursor" / ".cursorrules").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".gitconfig").exists()


def test_restore_dry_run(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test restore dry run."""
    repo = GitRepository(temp_git_repo)

    # Clean up any existing files to ensure the dry run has files to restore
    for path in [".cursor", ".vscode", ".gitconfig", ".gitignore"]:
        full_path = temp_git_repo / path
        if full_path.is_dir():
            shutil.rmtree(full_path)
        elif full_path.exists():
            full_path.unlink()

    # Perform dry run (no force needed since it's dry run)
    assert restore_manager.restore(repo.name, temp_git_repo, dry_run=True)


def test_restore_with_conflicts(
    restore_manager: RestoreManager, temp_git_repo: Path, backup_with_files: Path
) -> None:
    """Test restore with conflicts."""
    # Create conflicting files
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    (cursor_dir / ".cursorrules").write_text("modified rules")
    repo = GitRepository(temp_git_repo)

    # Attempt restore without force
    # With the new behavior, restore returns True if files were skipped
    result = restore_manager.restore(repo.name, temp_git_repo)
    assert result

    # Verify files were not overwritten
    assert (cursor_dir / ".cursorrules").read_text() == "modified rules"

    # Now restore with force
    result = restore_manager.restore(repo.name, temp_git_repo, force=True)
    assert result

    # Verify files were overwritten
    assert (cursor_dir / ".cursorrules").read_text() != "modified rules"
