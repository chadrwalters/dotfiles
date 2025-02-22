"""Shared test fixtures."""

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from dotfiles.core.backup import BackupManager
from dotfiles.core.bootstrap import BootstrapManager
from dotfiles.core.config import Config
from dotfiles.core.restore import RestoreManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with TemporaryDirectory() as temp:
        yield Path(temp)


@pytest.fixture
def backup_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary backup directory for tests."""
    backup_dir = temp_dir / "backups"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True)
    yield backup_dir
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    config = Config()
    config._merge_config(
        {
            "search_paths": ["/test/path1", "/test/path2"],
            "max_depth": 2,
            "exclude_patterns": ["test_exclude"],
            "programs": {
                "cursor": {
                    "name": "Cursor",
                    "paths": [".cursor/.cursorrules", ".cursor/"],
                    "files": [".cursor/.cursorrules", ".cursor/rules/test.mdc"],
                    "directories": [".cursor"],
                },
                "vscode": {
                    "name": "Visual Studio Code",
                    "paths": [".vscode/settings.json", ".vscode/"],
                    "files": [".vscode/settings.json", ".vscode/extensions.json"],
                    "directories": [".vscode"],
                },
                "git": {
                    "name": "Git",
                    "paths": [".gitconfig", ".gitignore"],
                    "files": [".gitconfig", ".gitignore"],
                    "directories": [],
                },
                "testprogram": {
                    "name": "Test Program",
                    "paths": [".testconfig", ".test/"],
                    "files": [".testconfig"],
                    "directories": [".test"],
                },
            },
        }
    )
    return config


@pytest.fixture
def backup_manager(test_config: Config, backup_dir: Path) -> BackupManager:
    """Create a backup manager with test configuration."""
    manager = BackupManager(test_config)
    manager.backup_dir = backup_dir
    return manager


@pytest.fixture
def temp_git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary Git repository."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)

    # Create and commit a test file
    test_file = repo_path / "test.txt"
    test_file.write_text("test content")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

    yield repo_path
    if repo_path.exists():
        shutil.rmtree(repo_path)


@pytest.fixture
def temp_workspace(temp_dir: Path, temp_git_repo: Path) -> Generator[Path, None, None]:
    """Create a temporary workspace with multiple repositories."""
    workspace = temp_dir / "workspace"
    workspace.mkdir()

    # Create multiple repositories
    for name in ["repo1", "repo2", "repo3"]:
        repo_path = workspace / name
        subprocess.run(["git", "clone", str(temp_git_repo), str(repo_path)], check=True)

    # Create some non-git directories
    (workspace / "not_a_repo").mkdir()
    (workspace / "excluded").mkdir()

    yield workspace


@pytest.fixture
def restore_manager(test_config: Config, backup_manager: BackupManager) -> RestoreManager:
    """Create a restore manager for testing."""
    return RestoreManager(test_config, backup_manager)


@pytest.fixture
def bootstrap_manager(test_config: Config, backup_manager: BackupManager) -> BootstrapManager:
    """Create a bootstrap manager for testing."""
    manager = BootstrapManager(test_config)
    manager.backup_manager = backup_manager
    return manager
