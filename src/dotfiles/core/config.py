"""Configuration management for dotfiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

console = Console()

DEFAULT_CONFIG: Dict[str, Any] = {
    "search_paths": ["~/projects", "~/source"],
    "max_depth": 3,
    "exclude_patterns": ["node_modules", "venv", ".venv", "env", ".env"],
    "backup_dir": "backups",
    "programs": {
        "cursor": {
            "name": "Cursor",
            "paths": [
                ".cursor/.cursorrules",
                ".cursor/rules/*.mdc",
                ".cursor/",
                ".cursor/prompts/*.md",
            ],
            "files": [".cursor/.cursorrules", ".cursor/rules/*.mdc", ".cursor/prompts/*.md"],
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
    """Configuration class for dotfiles."""

    def __init__(self) -> None:
        """Initialize configuration."""
        self.config: Dict[str, Any] = {}
        self.search_paths: List[str] = []
        self.max_depth: int = 3
        self.exclude_patterns: List[str] = []
        self.cursor_files: List[str] = []
        self.cursor_directories: List[str] = []
        self.programs: Dict[str, Dict[str, Any]] = {}
        self.load_config()

    def load_config(self, config_file: Optional[Path] = None) -> None:
        """Load configuration from file."""
        # Start with default configuration
        self._merge_config(DEFAULT_CONFIG)

        # If a config file is provided, load and merge it
        if config_file is not None:
            try:
                import yaml

                with open(config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(user_config)
            except Exception as e:
                console.print(f"[red]Error loading config file: {e}[/red]")

    def _merge_config(self, config: Dict[str, Any]) -> None:
        """Merge configuration with current configuration."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Update the raw config
        self.config.update(config)

        # Update search paths
        if "search_paths" in config:
            if not isinstance(config["search_paths"], list):
                raise ValueError("search_paths must be a list")
            self.search_paths = [str(Path(p).expanduser()) for p in config["search_paths"]]

        # Update max depth
        if "max_depth" in config:
            if not isinstance(config["max_depth"], int):
                raise ValueError("max_depth must be an integer")
            self.max_depth = config["max_depth"]

        # Update exclude patterns
        if "exclude_patterns" in config:
            if not isinstance(config["exclude_patterns"], list):
                raise ValueError("exclude_patterns must be a list")
            self.exclude_patterns = config["exclude_patterns"]

        # Update programs
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

                # Update cursor-specific attributes if this is the cursor program
                if program == "cursor":
                    self.cursor_files = program_config.get("files", [])
                    self.cursor_directories = program_config.get("directories", [])

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

    def load_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Load configuration from a dictionary.

        Args:
            config_data: Dictionary containing configuration data.

        Example:
            ```python
            config = Config()
            config_data = {
                "backup_dir": "~/backups",
                "cursor": {
                    "files": [".cursor/settings.json"],
                    "directories": [".cursor/rules"],
                },
            }
            config.load_from_dict(config_data)
            ```
        """
        self.config = config_data
        if "cursor" in config_data:
            cursor_config = config_data["cursor"]
            self.cursor_files = cursor_config.get("files", [])
            self.cursor_directories = cursor_config.get("directories", [])

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: The configuration key to get.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default if not found.
        """
        return self.config.get(key, default)
