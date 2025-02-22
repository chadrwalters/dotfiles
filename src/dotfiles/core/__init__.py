"""Core functionality for dotfiles management."""

from .branch import GitError, switch_branch
from .commands import COMMANDS
from .config import Config
from .repository import GitRepository, RepositoryManager

__all__ = [
    "Config",
    "GitError",
    "GitRepository",
    "RepositoryManager",
    "COMMANDS",
    "switch_branch",
]
