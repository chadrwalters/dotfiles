"""Configuration for dotfiles backup and restore."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, cast

import yaml


class ProgramConfig(TypedDict):
    name: str
    files: List[str]
    directories: List[str]


# Configuration for each program's files to backup
BACKUP_CONFIGS: Dict[str, ProgramConfig] = {
    "cursor": {
        "name": "Cursor",
        "files": [
            ".cursorrules",
            ".cursorsettings",
        ],
        "directories": [
            ".cursor",
        ],
    },
    "windsurf": {
        "name": "Windsurf",
        "files": [
            ".windsurfrules",
        ],
        "directories": [],
    },
    "vscode": {"name": "VSCode", "files": [], "directories": [".vscode"]},
    "git": {
        "name": "Git",
        "files": [
            ".gitignore",
            ".gitmessage",
            ".gitattributes",
        ],
        "directories": [],
    },
}

# Directory where backups will be stored
BACKUP_DIR = Path("backups")


class Config:
    """Legacy configuration class."""

    def __init__(self, config_file: Optional[Path] = None) -> None:
        """Initialize configuration."""
        self.config_file = config_file or Path.home() / ".config" / "dotfiles" / "config.yaml"
        self.config: Dict = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")

    def get_search_paths(self) -> List[str]:
        """Get repository search paths."""
        paths = self.config.get("search_paths", [])
        if isinstance(paths, str):
            paths = [paths]
        return cast(List[str], [str(os.path.expanduser(path)) for path in paths])

    def get_exclude_patterns(self) -> List[str]:
        """Get repository exclude patterns."""
        patterns = self.config.get("exclude_patterns", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        return cast(List[str], [str(pattern) for pattern in patterns])

    def get_program_path(self, program: str) -> str:
        """Get program path."""
        path = self.config.get("programs", {}).get(program, {}).get("path", "")
        if not isinstance(path, str):
            path = ""
        return str(os.path.expanduser(path)) if path else ""

    def get_all_programs(self) -> List[str]:
        """Get list of all configured programs."""
        programs = self.config.get("programs", {}).keys()
        return cast(List[str], list(programs))

    def get_program_name(self, program: str) -> str:
        """Get friendly name of a program."""
        name = self.config.get("programs", {}).get(program, {}).get("name", program)
        return str(name)


def get_program_files(program: str) -> List[str]:
    """Get list of files to backup for a program."""
    if program not in BACKUP_CONFIGS:
        return []
    return BACKUP_CONFIGS[program]["files"]


def get_program_dirs(program: str) -> List[str]:
    """Get list of directories to backup for a program."""
    if program not in BACKUP_CONFIGS:
        return []
    return BACKUP_CONFIGS[program]["directories"]


def get_sibling_dirs() -> List[Path]:
    """Get list of all sibling directories."""
    current_dir = Path.cwd()
    parent_dir = current_dir.parent
    return [
        d
        for d in parent_dir.iterdir()
        if d.is_dir() and d != current_dir and not d.name.startswith(".")
    ]


def get_sibling_repos() -> List[Path]:
    """Get list of sibling Git repositories."""
    return [d for d in get_sibling_dirs() if (d / ".git").exists()]
