"""Tests for wipe functionality."""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from dotfiles.core.repository import GitRepository
from dotfiles.core.wipe import WipeManager


@pytest.fixture
def wipe_manager(test_config: Any, temp_dir: Path) -> WipeManager:
    """Create a wipe manager with test configuration."""
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        return WipeManager(test_config)


@pytest.fixture
def repo_with_files(temp_git_repo: Path) -> GitRepository:
    """Create a repository with test files."""
    # Create test files
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    (cursor_dir / ".cursorrules").write_text("cursor rules")
    (cursor_dir / "rules").mkdir(exist_ok=True)
    (cursor_dir / "rules" / "test.mdc").write_text("test")

    vscode_dir = temp_git_repo / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    (vscode_dir / "settings.json").write_text('{"setting": "value"}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (temp_git_repo / ".gitconfig").write_text("[user]\n\tname = Test User")
    (temp_git_repo / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Initialize Git repository
    subprocess.run(["git", "init"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_git_repo, check=True)

    return GitRepository(temp_git_repo)


def test_wipe_program(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping a single program."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe cursor program
    assert wipe_manager.wipe(repo_with_files, programs=["cursor"])

    # Verify cursor files are removed but vscode files remain
    assert not (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_all_programs(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping all programs."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe all programs
    assert wipe_manager.wipe(repo_with_files)

    # Verify all files are removed
    assert not (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert not (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_specific_program(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping a specific program."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Wipe vscode program
    assert wipe_manager.wipe(repo_with_files, programs=["vscode"])

    # Verify vscode files are removed but cursor files remain
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert not (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_dry_run(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wipe dry run."""
    # Verify files exist
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()

    # Perform dry run
    assert wipe_manager.wipe(repo_with_files, dry_run=True)

    # Verify no files were removed
    assert (repo_with_files.path / ".cursor" / ".cursorrules").exists()
    assert (repo_with_files.path / ".vscode" / "settings.json").exists()


def test_wipe_unknown_program(wipe_manager: WipeManager, repo_with_files: GitRepository) -> None:
    """Test wiping unknown program."""
    assert not wipe_manager.wipe_program(repo_with_files, "unknown")


def test_wipe_empty_repo(wipe_manager: WipeManager, temp_git_repo: Path) -> None:
    """Test wiping empty repository."""
    repo = GitRepository(temp_git_repo)
    assert not wipe_manager.wipe(repo)
