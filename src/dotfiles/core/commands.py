"""Command functionality for dotfiles."""

from pathlib import Path
from typing import List

from rich.console import Console

from .config import Config
from .repository import GitRepository

console = Console()


def find_repositories(config: Config) -> List[GitRepository]:
    """Find Git repositories in configured search paths."""
    repos = []
    for search_path_str in config.search_paths:
        search_path = Path(search_path_str).expanduser()
        if not search_path.exists():
            continue
        repos.append(GitRepository(search_path))
    return repos
