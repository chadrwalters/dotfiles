"""Test backup module."""

import shutil
from pathlib import Path

import pytest

from dotfiles.core.backup import BackupManager
from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository


def create_test_files(repo_path: Path) -> None:
    """Create test files for backup testing."""
    # Create test directories
    cursor_dir = repo_path / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    (cursor_dir / "rules").mkdir(exist_ok=True)
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = repo_path / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (repo_path / ".gitconfig").write_text("[user]\n\tname = Test User")
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/")


@pytest.fixture
def backup_manager(test_config: Config) -> BackupManager:
    """Create a backup manager with test configuration."""
    manager = BackupManager(test_config)
    manager.backup_dir = Path("test_temp/backups")
    manager.backup_dir.mkdir(parents=True, exist_ok=True)
    return manager


def test_backup_path(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backup path generation."""
    repo = GitRepository(temp_git_repo)
    path = backup_manager.backup_path(repo)
    assert path.parent.name == repo.get_current_branch()
    assert path.parent.parent.name == repo.name


def test_list_backups_empty(backup_manager: BackupManager, temp_dir: Path) -> None:
    """Test listing backups when none exist."""
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert not backup_manager.list_backups()


def test_list_backups(backup_manager: BackupManager, temp_dir: Path) -> None:
    """Test listing backups."""
    # Create test backup structure
    repo_name = "test_repo"
    branch_name = "main"
    backup_dir = backup_manager.backup_dir / repo_name / branch_name
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = "20250101-120000"
    backup_path = backup_dir / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)

    # Create program directories
    (backup_path / "cursor").mkdir()
    (backup_path / "vscode").mkdir()

    # List backups
    backups = backup_manager.list_backups()
    assert len(backups) == 1
    assert backups[0].name == timestamp
    assert backups[0].parent.name == branch_name
    assert backups[0].parent.parent.name == repo_name


def test_backup_program(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backing up a single program."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Backup cursor program
    assert backup_manager.backup(repo, programs=["cursor"])

    # Get latest backup
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    backup_path = backups[0]

    # Verify cursor was backed up
    assert (backup_path / "cursor").exists()
    assert (backup_path / "cursor" / ".cursor" / ".cursorrules").exists()
    assert not (backup_path / "vscode").exists()
    assert not (backup_path / "git").exists()


def test_backup_all_programs(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backing up all programs."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Backup all programs
    assert backup_manager.backup(repo)

    # Get latest backup
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    backup_path = backups[0]

    # Verify all programs were backed up
    assert (backup_path / "cursor").exists()
    assert (backup_path / "vscode").exists()
    assert (backup_path / "git").exists()


def test_backup_specific_program(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backing up a specific program."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Backup only vscode
    assert backup_manager.backup(repo, programs=["vscode"])

    # Get latest backup
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    backup_path = backups[0]

    # Verify only vscode was backed up
    assert not (backup_path / "cursor").exists()
    assert (backup_path / "vscode").exists()
    assert not (backup_path / "git").exists()


def test_backup_dry_run(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backup dry run."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Perform dry run
    assert backup_manager.backup(repo, dry_run=True)

    # Verify no backup was created
    assert not backup_manager.list_backups(repo.name)


def test_backup_branch(backup_manager: BackupManager, temp_git_repo: Path) -> None:
    """Test backup with specific branch."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Create and switch to feature branch
    repo.path.joinpath("feature.txt").write_text("feature")
    shutil.rmtree(repo.path / ".cursor")  # Remove cursor directory

    # Backup with branch
    assert backup_manager.backup(repo, branch="feature")

    # Verify backup structure
    backups = backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    assert backups[0].parent.name == "feature"
