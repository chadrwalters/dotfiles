"""Wipe functionality for dotfiles."""

from __future__ import annotations

import glob
import shutil
from pathlib import Path
from typing import List, Optional, Set

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

    def get_program_paths(self, repo: GitRepository, program: str) -> Set[Path]:
        """Get all paths that would be wiped for a program.

        Args:
            repo: Git repository to get paths for.
            program: Program to get paths for.

        Returns:
            Set of paths to wipe.
        """
        paths = set()
        program_config = self.config.get_program_config(program)
        if not program_config:
            return paths

        # Get paths to wipe
        files = program_config.get("files", [])
        directories = program_config.get("directories", [])

        # Add directory paths first (they might contain files we want to wipe)
        for dir_pattern in directories:
            # Handle glob patterns
            if "*" in dir_pattern:
                pattern = str(repo.path / dir_pattern)
                for path in glob.glob(pattern, recursive=True):
                    path = Path(path)
                    if path.is_dir() and path.exists() and any(path.iterdir()):
                        paths.add(path)
            else:
                dir_path = repo.path / dir_pattern
                if dir_path.is_dir() and dir_path.exists() and any(dir_path.iterdir()):
                    paths.add(dir_path)

        # Add file paths
        for file_pattern in files:
            # Handle glob patterns
            if "*" in file_pattern:
                pattern = str(repo.path / file_pattern)
                for path in glob.glob(pattern, recursive=True):
                    path = Path(path)
                    if path.is_file() and path.exists() and path.stat().st_size > 0:
                        paths.add(path)
            else:
                file_path = repo.path / file_pattern
                if file_path.is_file() and file_path.exists() and file_path.stat().st_size > 0:
                    paths.add(file_path)

        return paths

    def wipe_program(
        self,
        repo: GitRepository,
        program: str,
        dry_run: bool = False,
    ) -> bool:
        """Wipe program configurations."""
        paths = self.get_program_paths(repo, program)
        if not paths:
            return False

        # Check if any of the paths actually exist and have content
        existing_paths = [
            p
            for p in paths
            if p.exists()
            and (p.is_file() and p.stat().st_size > 0 or p.is_dir() and any(p.iterdir()))
        ]
        if not existing_paths:
            return False

        wiped = False

        try:
            # First wipe directories to avoid issues with files within them
            for path in sorted(existing_paths, reverse=True):
                if path.is_dir():
                    if not dry_run:
                        shutil.rmtree(path)
                    wiped = True

            # Then wipe files
            for path in sorted(existing_paths):
                if path.is_file():
                    if not dry_run:
                        path.unlink()
                    wiped = True

        except Exception as e:
            console.print(f"[red]Error wiping {program}: {e}")
            return False

        return wiped

    def wipe(
        self,
        repo: GitRepository,
        programs: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False,
        testing: bool = False,
    ) -> bool:
        """Wipe configurations."""
        # Get list of programs to wipe
        if programs is None:
            programs = list(self.config.programs.keys())

        # Check if any program has files to wipe
        has_files = False
        for program in programs:
            paths = self.get_program_paths(repo, program)
            if paths and any(
                p.exists()
                and (p.is_file() and p.stat().st_size > 0 or p.is_dir() and any(p.iterdir()))
                for p in paths
            ):
                has_files = True
                break

        if not has_files:
            self.console.print("[yellow]Warning: No configurations found to wipe")
            return False

        # Check what would be wiped
        all_paths = set()
        for program in programs:
            paths = self.get_program_paths(repo, program)
            if paths:
                # Only include paths that actually exist and have content
                existing_paths = [
                    p
                    for p in paths
                    if p.exists()
                    and (p.is_file() and p.stat().st_size > 0 or p.is_dir() and any(p.iterdir()))
                ]
                if existing_paths:
                    all_paths.update(existing_paths)

        if not all_paths:
            self.console.print("[yellow]Warning: No configurations found to wipe")
            return False

        # If not forcing and not in testing mode, show what would be wiped
        if not force and not dry_run and not testing:
            self.console.print("\nThe following files and directories will be wiped:")
            for path in sorted(all_paths):
                self.console.print(f"  - {path}")
            if not self.console.input("\nContinue? [y/N] ").lower().startswith("y"):
                self.console.print("Aborted.")
                return False

        any_wiped = False
        # Wipe each program
        with Live(Spinner("dots"), refresh_per_second=10) as live:
            for program in programs:
                live.update(Spinner("dots", f"Wiping {program} configurations..."))
                if self.wipe_program(repo, program, dry_run):
                    any_wiped = True

        if not any_wiped:
            self.console.print("[yellow]Warning: No configurations were wiped")
            return False

        if dry_run:
            self.console.print("[yellow]Dry run completed. No files were wiped.")
        else:
            self.console.print("[green]Configurations wiped successfully.")

        return any_wiped
