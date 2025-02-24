"""Core functionality for dotfiles."""

from .backup import BackupManager
from .config import Config
from .repository import GitRepository
from .restore import RestoreManager

__all__ = ["BackupManager", "Config", "GitRepository", "RestoreManager"]
