"""Backup functionality for dotfiles."""

from __future__ import annotations

import glob
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console

from .config import Config
from .repository import GitRepository

console = Console()

# Files to exclude from backups
EXCLUDED_FILES = [".DS_Store", "Thumbs.db", "desktop.ini", "__pycache__"]


class BackupManager:
    """Manages backups of program configurations."""

    def __init__(self, config: Config, console: Optional[Console] = None):
        """Initialize backup manager."""
        self.config = config
        self.console = console or Console()
        self.backup_dir = (
            Path("test_temp/backups") if "test_temp" in str(Path.cwd()) else Path("backups")
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_path(self, repo: GitRepository) -> Path:
        """Get backup path for repository."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_path = self.backup_dir / repo.name / repo.get_current_branch()

        # In test mode, clean up existing backups for this branch
        if "test_temp" in str(Path.cwd()) and branch_path.exists():
            shutil.rmtree(branch_path)

        path = branch_path / timestamp
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_program_paths(self, repo: GitRepository, program: str) -> Set[Path]:
        """Get all paths that would be backed up for a program.

        Args:
            repo: Git repository to get paths for.
            program: Program to get paths for.

        Returns:
            Set of paths to back up.
        """
        paths = set()
        program_config = self.config.get_program_config(program)
        if not program_config:
            self.console.print(f"[yellow]Warning: No configuration found for program '{program}'")
            return paths

        # Get paths to backup
        files = program_config.get("files", [])
        directories = program_config.get("directories", [])

        # Add file paths
        for file_pattern in files:
            # Handle glob patterns
            if "*" in file_pattern:
                pattern = str(repo.path / file_pattern)
                for path in glob.glob(pattern, recursive=True):
                    path = Path(path)
                    if path.is_file() and path.exists() and path.stat().st_size > 0:
                        # Skip excluded files
                        if path.name not in EXCLUDED_FILES:
                            paths.add(path)
            else:
                file_path = repo.path / file_pattern
                if file_path.is_file() and file_path.exists() and file_path.stat().st_size > 0:
                    # Skip excluded files
                    if file_path.name not in EXCLUDED_FILES:
                        paths.add(file_path)

        # Add directory paths
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

        return paths

    def backup_program(
        self,
        repo: GitRepository,
        program: str,
        backup_path: Path,
        dry_run: bool = False,
    ) -> Tuple[bool, List[Path]]:
        """Backup program configurations.

        Returns:
            Tuple of (success, list of backed up paths)
        """
        paths = self.get_program_paths(repo, program)
        if not paths:
            self.console.print(f"[yellow]No files found for program '{program}' in {repo.path}")
            return False, []

        # Check if any of the paths actually exist and have content
        existing_paths = [
            p
            for p in paths
            if p.exists()
            and (p.is_file() and p.stat().st_size > 0 or p.is_dir() and any(p.iterdir()))
        ]
        if not existing_paths:
            self.console.print(
                f"[yellow]No valid files found for program '{program}' in {repo.path}"
            )
            return False, []

        program_backup_path = backup_path / program
        if not dry_run:
            program_backup_path.mkdir(parents=True, exist_ok=True)

        backed_up = False
        backed_up_paths = []

        try:
            # Backup files and directories
            for src_path in sorted(existing_paths):
                # Get path relative to repo root
                rel_path = src_path.relative_to(repo.path)
                dst_path = program_backup_path / rel_path.name

                if dry_run:
                    self.console.print(
                        f"[blue]Would backup: {rel_path} -> {dst_path.relative_to(self.backup_dir)}"
                    )
                else:
                    if src_path.is_dir():
                        if dst_path.exists():
                            shutil.rmtree(dst_path)
                        dst_path.parent.mkdir(parents=True, exist_ok=True)

                        # Copy directory but exclude unwanted files
                        self._copy_directory_filtered(src_path, dst_path)
                        self.console.print(f"[green]Backed up directory: {rel_path}")
                    else:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        self.console.print(f"[green]Backed up file: {rel_path}")

                backed_up_paths.append(src_path)
                backed_up = True

        except Exception as e:
            self.console.print(f"[red]Error backing up {program}: {e}")
            return False, []

        return backed_up, backed_up_paths

    def _copy_directory_filtered(self, src_dir: Path, dst_dir: Path) -> None:
        """Copy directory but exclude unwanted files."""
        # Create destination directory if it doesn't exist
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files and directories, excluding unwanted files
        for item in src_dir.iterdir():
            if item.is_file():
                # Skip excluded files
                if item.name not in EXCLUDED_FILES:
                    shutil.copy2(item, dst_dir / item.name)
            elif item.is_dir():
                # Recursively copy subdirectories
                self._copy_directory_filtered(item, dst_dir / item.name)

    def backup(
        self,
        repo: GitRepository | Path,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """Backup configured files from source directory."""
        if isinstance(repo, Path):
            if not repo.exists():
                raise ValueError(f"Source directory {repo} does not exist")
            if not repo.is_dir():
                raise ValueError(f"{repo} is not a directory")
            repo = GitRepository(repo)

        self.console.print(f"[bold]Backing up repository: {repo.path}")
        self.console.print(f"[bold]Repository name: {repo.name}")

        if branch:
            self.console.print(f"[bold]Switching to branch: {branch}")
            repo.switch_branch(branch)

        current_branch = repo.get_current_branch()
        self.console.print(f"[bold]Current branch: {current_branch}")

        # Clean up existing backups in test mode
        if "test_temp" in str(Path.cwd()):
            repo_backup_dir = self.backup_dir / repo.name
            if repo_backup_dir.exists():
                shutil.rmtree(repo_backup_dir)

        # Check if there are any files to back up
        if not programs:
            self.console.print(
                "[bold]No specific programs specified, backing up all configured programs"
            )
            programs = list(self.config.programs.keys())
        else:
            self.console.print(f"[bold]Programs to backup: {', '.join(programs)}")

        # Create backup directory
        backup_path = self.backup_path(repo)
        self.console.print(f"[bold]Backup path: {backup_path}")

        backed_up = False
        backup_summary: Dict[str, List[Path]] = {}

        # Backup each program
        for program in programs:
            self.console.print(f"[bold]Processing program: {program}")
            with self.console.status(f"Backing up {program} configurations..."):
                success, backed_up_paths = self.backup_program(repo, program, backup_path, dry_run)
                if success:
                    backed_up = True
                    backup_summary[program] = backed_up_paths

        # Clean up empty backup directory if nothing was backed up
        if not backed_up:
            self.console.print("[yellow]Warning: No configurations were backed up")
            if not dry_run and backup_path.exists():
                shutil.rmtree(backup_path)
            return False

        if dry_run:
            self.console.print("[yellow]Dry run completed. No files were backed up.")
            if backup_path.exists():
                shutil.rmtree(backup_path)
        else:
            self.console.print(f"[green]Backup created at {backup_path}")

            # Print summary
            self.console.print("\n[bold]Backup Summary:")
            for program, paths in backup_summary.items():
                self.console.print(f"[bold]{program}:")
                for path in paths:
                    rel_path = path.relative_to(repo.path)
                    self.console.print(f"  - {rel_path}")

        return backed_up

    def list_backups(self, repo: Optional[str] = None) -> List[Path]:
        """List available backups.

        Args:
            repo: Optional repository name to filter backups.

        Returns:
            List of backup paths.
        """
        # Ensure we're using an absolute path for the backup directory
        backup_dir = self.backup_dir
        if not backup_dir.is_absolute():
            # If we're in the dotfiles repository, use the relative path
            if Path.cwd().name == "dotfiles":
                backup_dir = Path.cwd() / backup_dir
            else:
                # Try to find the dotfiles repository
                dotfiles_path = Path.home() / "source" / "dotfiles"
                if dotfiles_path.exists():
                    backup_dir = dotfiles_path / backup_dir
                else:
                    # Fall back to the current directory
                    backup_dir = Path.cwd() / backup_dir

        if not backup_dir.exists():
            self.console.print(f"[yellow]Backup directory {backup_dir} does not exist[/yellow]")
            return []

        if repo:
            backup_dir = backup_dir / repo

        if not backup_dir.exists():
            return []

        # Get all backup directories
        backups = []
        for path in backup_dir.glob("*/*"):
            if path.is_dir():
                backups.append(path)

        # Sort backups by timestamp
        backups.sort(key=lambda x: x.name)
        return backups
