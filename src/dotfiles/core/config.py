"""Configuration management for dotfiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import yaml
from rich.console import Console

console = Console()

DEFAULT_CONFIG: Dict[str, Any] = {
    "search_paths": ["~/projects", "~/source"],
    "max_depth": 3,
    "exclude_patterns": ["node_modules", "venv", ".venv", "env", ".env"],
    "programs": {
        "cursor": {
            "name": "Cursor",
            "paths": [".cursorrules", ".cursor/rules/*.mdc", ".cursor/"],
            "files": [".cursorrules", ".cursor/rules/*.mdc"],
            "directories": [".cursor"],
        },
        "windsurf": {
            "name": "Windsurf",
            "paths": [".windsurfrules"],
            "files": [".windsurfrules"],
            "directories": [],
        },
        "vscode": {
            "name": "Visual Studio Code",
            "paths": [".vscode/settings.json", ".vscode/extensions.json", ".vscode/"],
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


class Config:
    """Configuration class."""

    def __init__(self) -> None:
        """Initialize configuration."""
        self.search_paths: List[str] = [
            str(Path(p).expanduser()) for p in DEFAULT_CONFIG["search_paths"]
        ]
        self.max_depth: int = DEFAULT_CONFIG["max_depth"]
        self.exclude_patterns: List[str] = DEFAULT_CONFIG["exclude_patterns"].copy()
        self.programs: Dict[str, Dict[str, Any]] = cast(
            Dict[str, Dict[str, Any]], DEFAULT_CONFIG["programs"].copy()
        )

    def load_config(self, config_path: Path) -> None:
        """Load configuration from file."""
        if not config_path.exists():
            return

        with config_path.open() as f:
            config = yaml.safe_load(f)
            if config:
                self._merge_config(config)

    def _merge_config(self, config: Dict[str, Any]) -> None:
        """Merge configuration with current configuration."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        if "search_paths" in config:
            if not isinstance(config["search_paths"], list):
                raise ValueError("search_paths must be a list")
            self.search_paths = [str(Path(p).expanduser()) for p in config["search_paths"]]

        if "max_depth" in config:
            if not isinstance(config["max_depth"], int):
                raise ValueError("max_depth must be an integer")
            self.max_depth = config["max_depth"]

        if "exclude_patterns" in config:
            if not isinstance(config["exclude_patterns"], list):
                raise ValueError("exclude_patterns must be a list")
            self.exclude_patterns = config["exclude_patterns"]

        if "programs" in config:
            if not isinstance(config["programs"], dict):
                raise ValueError("programs must be a dictionary")
            for program, program_config in config["programs"].items():
                if not isinstance(program_config, dict):
                    raise ValueError(f"Program configuration for {program} must be a dictionary")
                if "name" not in program_config:
                    raise ValueError(f"Program configuration for {program} must have a name")

                # Create a copy to avoid modifying the input
                program_config = program_config.copy()

                # Convert old format to new format
                if "files" in program_config or "directories" in program_config:
                    paths = []
                    files = program_config.get("files", [])
                    directories = program_config.get("directories", [])
                    if not isinstance(files, list):
                        raise ValueError(f"Program files for {program} must be a list")
                    if not isinstance(directories, list):
                        raise ValueError(f"Program directories for {program} must be a list")
                    paths.extend(files)
                    paths.extend(d + "/" for d in directories)  # Add trailing slash for directories
                    program_config["paths"] = paths
                elif "paths" not in program_config:
                    raise ValueError(f"Program configuration for {program} must have paths")
                elif not isinstance(program_config["paths"], list):
                    raise ValueError(f"Program paths for {program} must be a list")

                # Convert new format to old format
                if "paths" in program_config:
                    program_config["files"] = [
                        p.rstrip("/") for p in program_config["paths"] if not p.endswith("/")
                    ]
                    program_config["directories"] = [
                        p.rstrip("/") for p in program_config["paths"] if p.endswith("/")
                    ]

                if program in self.programs:
                    self.programs[program].update(program_config)
                else:
                    self.programs[program] = program_config

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        # Validate search paths
        if not isinstance(self.search_paths, list):
            errors.append("search_paths must be a list")
        else:
            for path in self.search_paths:
                if not isinstance(path, str):
                    errors.append(f"search path {path} must be a string")

        # Validate max depth
        if not isinstance(self.max_depth, int):
            errors.append("max_depth must be an integer")

        # Validate exclude patterns
        if not isinstance(self.exclude_patterns, list):
            errors.append("exclude_patterns must be a list")
        else:
            for pattern in self.exclude_patterns:
                if not isinstance(pattern, str):
                    errors.append(f"exclude pattern {pattern} must be a string")

        # Validate programs
        if not isinstance(self.programs, dict):
            errors.append("programs must be a dictionary")
        else:
            for program, config in self.programs.items():
                if not isinstance(config, dict):
                    errors.append(f"program {program} configuration must be a dictionary")
                    continue

                if "name" not in config:
                    errors.append(f"program {program} configuration must have a name")
                elif not isinstance(config["name"], str):
                    errors.append(f"program {program} name must be a string")

                if "paths" not in config:
                    errors.append(f"program {program} configuration must have paths")
                elif not isinstance(config["paths"], list):
                    errors.append(f"program {program} paths must be a list")
                else:
                    for path in config["paths"]:
                        if not isinstance(path, str):
                            errors.append(f"program {program} path {path} must be a string")

        return errors

    def get_program_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all program configurations."""
        return self.programs

    def get_program_config(self, program: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific program."""
        return self.programs.get(program)
