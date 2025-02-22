"""Repository discovery and management."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rich.console import Console

from .config import Config

console = Console()


class GitRepository:
    """Represents a Git repository."""

    def __init__(self, path: Path):
        """Initialize repository."""
        self.path = path
        self.name = path.name

    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"  # Default to main if Git command fails

    def has_changes(self) -> bool:
        """Check if repository has uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def run_git_command(self, command: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """Run a Git command in this repository."""
        return subprocess.run(
            ["git", "-C", str(self.path)] + command,
            capture_output=True,
            text=True,
            check=True,
            **kwargs,
        )

    @property
    def branches(self) -> List[str]:
        """Get list of branches."""
        try:
            result = self.run_git_command(["branch", "--list", "--format=%(refname:short)"])
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []

    @property
    def current_branch(self) -> str:
        """Get current branch name."""
        return self.get_current_branch()


class RepositoryManager:
    """Manages Git repository discovery and operations."""

    def __init__(self, config: Config):
        """Initialize repository manager."""
        self.config = config
        self._repo_cache: Dict[str, GitRepository] = {}
        self._cache_file = Path.home() / ".cache" / "dotfiles" / "repos.cache"

    def _is_excluded(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(str(path), pattern) or any(
                fnmatch.fnmatch(part, pattern) for part in path.parts
            ):
                return True
        return False

    def find_repositories(self, force_scan: bool = False) -> List[GitRepository]:
        """Find Git repositories in configured search paths."""
        if not force_scan and self._repo_cache:
            return list(self._repo_cache.values())

        repos: Set[GitRepository] = set()
        for search_path_str in self.config.search_paths:
            search_path = Path(search_path_str).expanduser()
            if not search_path.exists():
                continue

            # First check if the search path itself is a repository
            if (search_path / ".git").exists():
                repos.add(GitRepository(search_path))
                continue

            # Then search for repositories up to max_depth
            for git_dir in search_path.rglob(".git"):
                if not git_dir.is_dir():
                    continue

                repo_path = git_dir.parent
                depth = len(repo_path.relative_to(search_path).parts)
                if depth > self.config.max_depth:
                    continue

                # Check exclude patterns
                if any(
                    pattern in str(repo_path.relative_to(search_path))
                    for pattern in self.config.exclude_patterns
                ):
                    continue

                repos.add(GitRepository(repo_path))

        self._repo_cache = {repo.name: repo for repo in repos}
        return list(repos)

    def get_repository(self, name_or_path: str) -> Optional[GitRepository]:
        """Get repository by name or path."""
        # First try to find by name in cache
        if name_or_path in self._repo_cache:
            return self._repo_cache[name_or_path]

        # If not in cache, try to find by path
        repo_path = Path(name_or_path).expanduser()
        if repo_path.exists():
            # Check if it's a Git repository
            if (repo_path / ".git").exists():
                repo = GitRepository(repo_path)
                self._repo_cache[repo.name] = repo
                return repo

            # Check if it's a path within a repository
            for parent in repo_path.parents:
                if (parent / ".git").exists():
                    repo = GitRepository(parent)
                    self._repo_cache[repo.name] = repo
                    return repo

        # If not found by path, try to find by name
        self.find_repositories()
        return self._repo_cache.get(name_or_path)

    def list_repositories(self) -> List[GitRepository]:
        """List all repositories."""
        return self.find_repositories()

    def _load_cache(self) -> bool:
        """Load repository cache."""
        try:
            if self._cache_file.exists():
                cache_data = self._cache_file.read_text().splitlines()
                for path_str in cache_data:
                    path = Path(path_str)
                    if path.is_dir():
                        repo = GitRepository(path)
                        self._repo_cache[repo.name] = repo
                return True
        except Exception as e:
            console.print(f"[yellow]Warning:[/] Failed to load repository cache: {e}")
        return False

    def _save_cache(self) -> None:
        """Save repository cache."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = "\n".join(str(repo.path) for repo in self._repo_cache.values())
            self._cache_file.write_text(cache_data)
        except Exception as e:
            console.print(f"[yellow]Warning:[/] Failed to save repository cache: {e}")
