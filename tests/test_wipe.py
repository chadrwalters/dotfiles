"""Test wipe functionality."""

from pathlib import Path

import pytest

from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository
from dotfiles.core.wipe import WipeManager

from .test_backup import create_test_files


@pytest.fixture
def wipe_manager(test_config: Config) -> WipeManager:
    """Create a wipe manager for testing."""
    return WipeManager(test_config)


@pytest.fixture
def repo_with_files(temp_git_repo: Path) -> GitRepository:
    """Create a repository with test files."""
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

    # Initialize Git repository
    repo = GitRepository(temp_git_repo)
    repo.init()
    repo.add(".")
    repo.commit("Initial commit")

    return repo


def test_wipe_program(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping a single program."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe cursor program
    assert wipe_manager.wipe(repo_with_files, programs=["cursor"], testing=True)

    # Verify cursor files are removed but vscode files remain
    assert not (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_all_programs(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping all programs."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe all programs
    assert wipe_manager.wipe(repo_with_files, testing=True)

    # Verify all files are removed
    assert not (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert not (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_specific_program(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping a specific program."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe vscode program
    assert wipe_manager.wipe(repo_with_files, programs=["vscode"], testing=True)

    # Verify vscode files are removed but cursor files remain
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert not (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_dry_run(wipe_manager: WipeManager, temp_git_repo: Path) -> None:
    """Test wipe dry run."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Perform dry run
    assert wipe_manager.wipe(repo, dry_run=True)

    # Verify files still exist
    assert (temp_git_repo / ".cursor" / ".cursorrules").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".gitconfig").exists()


def test_wipe_force(wipe_manager: WipeManager, temp_git_repo: Path) -> None:
    """Test wipe dry run."""
    create_test_files(temp_git_repo)
    repo = GitRepository(temp_git_repo)

    # Perform dry run
    assert wipe_manager.wipe(repo, dry_run=True)

    # Verify files still exist
    assert (temp_git_repo / ".cursor" / ".cursorrules").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".gitconfig").exists()
