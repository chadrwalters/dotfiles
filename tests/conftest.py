"""Test configuration."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from dotfiles.core.backup import BackupManager
from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository
from dotfiles.core.restore import RestoreManager
from dotfiles.core.wipe import WipeManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_dir = Path("test_temp")
    temp_dir.mkdir(exist_ok=True)
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary Git repository for testing."""
    repo_dir = temp_dir / "git_repo"
    repo_dir.mkdir(exist_ok=True)

    # Initialize Git repository using GitRepository class
    repo = GitRepository(repo_dir)
    repo.init()

    yield repo_dir


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration with cursor-focused settings."""
    config = Config()
    config_data: Dict[str, Any] = {
        "backup_dir": "test_temp/backups",
        "cursor": {
            "files": [
                ".cursor/.cursorrules",
                ".cursor/settings.json",
                ".cursor/keybindings.json",
                ".cursor/tasks.json",
                ".cursor/user-data.json",
            ],
            "directories": [
                ".cursor/snippets",
                ".cursor/extensions",
                ".cursor/rules",
                ".cursor/workspaces",
            ],
        },
    }
    config.load_from_dict(config_data)
    return config


@pytest.fixture
def test_repo(temp_dir: Path) -> GitRepository:
    """Create a test repository."""
    repo_dir = temp_dir / "test_repo"
    repo_dir.mkdir(exist_ok=True)

    # Create test files
    cursor_dir = repo_dir / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    (cursor_dir / "rules").mkdir(exist_ok=True)
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = repo_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (repo_dir / ".gitconfig").write_text("[user]\n\tname = Test User")
    (repo_dir / ".gitignore").write_text("*.pyc\n__pycache__/")

    return GitRepository(repo_dir)


@pytest.fixture
def backup_dir(temp_dir: Path) -> Path:
    """Create a temporary backup directory for testing."""
    backup_dir = temp_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


@pytest.fixture
def backup_manager(test_config: Config) -> BackupManager:
    """Create a backup manager for testing."""
    manager = BackupManager(test_config)
    manager.backup_dir = Path("test_temp/backups")
    if manager.backup_dir.exists():
        shutil.rmtree(manager.backup_dir)
    manager.backup_dir.mkdir(parents=True, exist_ok=True)
    return manager


@pytest.fixture
def restore_manager(test_config: Config, backup_manager: BackupManager) -> RestoreManager:
    """Create a restore manager for testing."""
    manager = RestoreManager(test_config, backup_manager)
    manager.backup_dir = backup_manager.backup_dir
    return manager


@pytest.fixture
def wipe_manager(test_config: Config) -> WipeManager:
    """Create a wipe manager for testing."""
    return WipeManager(test_config)
