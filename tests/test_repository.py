"""Tests for repository management."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from dotfiles.core.config import Config
from dotfiles.core.repository import GitRepository, RepositoryManager


@pytest.fixture
def temp_git_repo() -> Generator[Path, None, None]:
    """Create a temporary Git repository."""
    with TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
        )

        # Create and commit a test file
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

        yield repo_path


@pytest.fixture
def temp_workspace(temp_git_repo: Path) -> Generator[Path, None, None]:
    """Create a temporary workspace with multiple repositories."""
    with TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)

        # Create multiple repositories
        for name in ["repo1", "repo2", "repo3"]:
            repo_path = workspace / name
            subprocess.run(["git", "clone", str(temp_git_repo), str(repo_path)], check=True)

        # Create some non-git directories
        (workspace / "not_a_repo").mkdir()
        (workspace / "excluded").mkdir()

        yield workspace


def test_git_repository(temp_git_repo: Path) -> None:
    """Test GitRepository class."""
    repo = GitRepository(temp_git_repo)

    # Test basic properties
    assert repo.name == temp_git_repo.name
    assert repo.current_branch in [
        "master",
        "main",
    ]  # Different Git versions use different defaults
    assert repo.branches
    assert not repo.has_changes()

    # Test with changes
    test_file = temp_git_repo / "new.txt"
    test_file.write_text("new content")
    assert repo.has_changes()


def test_repository_manager(temp_workspace: Path) -> None:
    """Test RepositoryManager class."""
    config = Config()
    config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
            "exclude_patterns": ["excluded", "not_a_repo"],
        }
    )

    manager = RepositoryManager(config)
    repos = manager.find_repositories(force_scan=True)

    # Should find all three repositories
    assert len(repos) == 3
    repo_names = {repo.name for repo in repos}
    assert repo_names == {"repo1", "repo2", "repo3"}

    # Test repository lookup
    repo = manager.get_repository("repo1")
    assert repo is not None
    assert repo.name == "repo1"


def test_repository_caching(temp_workspace: Path) -> None:
    """Test repository cache functionality."""
    config = Config()
    config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )

    # First scan
    manager = RepositoryManager(config)
    first_scan = manager.find_repositories(force_scan=True)

    # Second scan should use cache
    second_scan = manager.find_repositories(force_scan=False)
    assert len(first_scan) == len(second_scan)

    # Force scan should work even with cache
    force_scan = manager.find_repositories(force_scan=True)
    assert len(force_scan) == len(first_scan)


def test_repository_depth_limit(temp_workspace: Path) -> None:
    """Test repository depth limiting."""
    # Create a deeply nested repository
    deep_path = temp_workspace / "deep" / "deeper" / "deepest"
    deep_path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=deep_path, check=True)

    config = Config()
    config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
            "max_depth": 2,  # Should not find the deepest repository
        }
    )

    manager = RepositoryManager(config)
    repos = manager.find_repositories(force_scan=True)

    # Should not find the deep repository
    deep_repo_found = any(repo.path == deep_path for repo in repos)
    assert not deep_repo_found


def test_repository_exclusions(temp_workspace: Path) -> None:
    """Test repository exclusion patterns."""
    # Create a repository in an excluded directory
    excluded_path = temp_workspace / "node_modules" / "repo"
    excluded_path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=excluded_path, check=True)

    config = Config()
    config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
            "exclude_patterns": ["node_modules"],
        }
    )

    manager = RepositoryManager(config)
    repos = manager.find_repositories(force_scan=True)

    # Should not find the excluded repository
    excluded_repo_found = any(repo.path == excluded_path for repo in repos)
    assert not excluded_repo_found


@pytest.fixture
def repo_manager(test_config: Config) -> RepositoryManager:
    """Create test repository manager."""
    return RepositoryManager(test_config)


def test_list_repositories_empty(repo_manager: RepositoryManager, temp_dir: Path) -> None:
    """Test listing repositories when none exist."""
    repo_manager.config._merge_config(
        {
            "search_paths": [str(temp_dir)],
        }
    )
    assert not repo_manager.list_repositories()


def test_list_repositories(repo_manager: RepositoryManager, temp_workspace: Path) -> None:
    """Test listing repositories."""
    repo_manager.config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )
    repos = repo_manager.list_repositories()
    assert len(repos) == 3
    assert any(r.name == "repo1" for r in repos)
    assert any(r.name == "repo2" for r in repos)
    assert any(r.name == "repo3" for r in repos)


def test_get_repository(repo_manager: RepositoryManager, temp_workspace: Path) -> None:
    """Test getting a specific repository."""
    repo_manager.config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )
    repo = repo_manager.get_repository("repo1")
    assert repo is not None
    assert repo.name == "repo1"
    assert repo.path == temp_workspace / "repo1"


def test_get_repository_nonexistent(repo_manager: RepositoryManager, temp_workspace: Path) -> None:
    """Test getting a nonexistent repository."""
    repo_manager.config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )
    assert repo_manager.get_repository("nonexistent") is None


def test_get_repository_by_path(repo_manager: RepositoryManager, temp_workspace: Path) -> None:
    """Test getting a repository by path."""
    repo_manager.config._merge_config(
        {
            "search_paths": [str(temp_workspace)],
        }
    )
    repo = repo_manager.get_repository(str(temp_workspace / "repo1"))
    assert repo is not None
    assert repo.name == "repo1"
    assert repo.path == temp_workspace / "repo1"
