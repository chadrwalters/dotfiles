"""Wipe functionality for dotfiles."""

from __future__ import annotations

import shutil
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from .config import Config
from .repository import GitRepository

console = Console()


class WipeManager:
    """Wipe manager class."""

    def __init__(self, config: Config) -> None:
        """Initialize wipe manager."""
        self.config = config
        self.console = Console()

    def wipe_program(self, repo: GitRepository, program: str, dry_run: bool = False) -> bool:
        """Wipe program configurations."""
        program_config = self.config.get_program_config(program)
        if not program_config:
            return False

        wiped = False
        try:
            # Get paths to wipe
            files = program_config.get("files", [])
            directories = program_config.get("directories", [])

            # Wipe directories first (they might contain files we want to wipe)
            for dir_pattern in directories:
                dir_path = repo.path / dir_pattern
                if dir_path.exists() and dir_path.is_dir():
                    if not dry_run:
                        shutil.rmtree(dir_path)
                    wiped = True

            # Then wipe individual files that might be outside directories
            for file_pattern in files:
                file_path = repo.path / file_pattern
                if file_path.exists() and file_path.is_file():
                    if not dry_run:
                        file_path.unlink()
                    wiped = True

        except Exception as e:
            self.console.print(f"Error wiping {program}: {e}")
            return False

        return wiped

    def wipe(
        self,
        repo: GitRepository,
        programs: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> bool:
        """Wipe configurations."""
        # Get list of programs to wipe
        if programs is None:
            programs = list(self.config.programs.keys())

        any_wiped = False

        with Live(Spinner("dots"), refresh_per_second=10) as live:
            for program in programs:
                live.update(Spinner("dots", f"Wiping {program} configurations..."))
                if self.wipe_program(repo, program, dry_run):
                    any_wiped = True

        if not any_wiped:
            self.console.print("Warning: No configurations were wiped")
            return False

        return True
