"""Backup functionality for Cursor IDE configuration files.

This module provides functionality for backing up Cursor IDE configuration files
from Git repositories. It handles backing up specific files and directories
defined in the configuration, with support for glob patterns and exclusions.
"""

from __future__ import annotations

import glob
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console

from .config import Config
from .repository import GitRepository
from .zip_export import ZipExporter

console = Console()

# Files to exclude from backups
EXCLUDED_FILES = [".DS_Store", "Thumbs.db", "desktop.ini", "__pycache__"]


class BackupManager:
    """Manages backups of Cursor IDE configuration files.

    This class handles the backup process for Cursor IDE configuration files,
    including:
    - Determining which files and directories to back up
    - Creating timestamped backup directories
    - Copying files while preserving metadata
    - Handling branch-specific backups
    - Supporting dry-run mode for backup validation

    Attributes:
        config (Config): Configuration object containing backup settings
        console (Console): Rich console for output formatting
        backup_dir (Path): Root directory for storing backups
    """

    def __init__(self, config: Config, console: Optional[Console] = None):
        """Initialize the backup manager.

        Args:
            config (Config): Configuration object containing backup settings
            console (Optional[Console]): Rich console for output. If None, creates
                                      a new console.
        """
        self.config = config
        self.console = console or Console()
        self.backup_dir = (
            Path("test_temp/backups") if "test_temp" in str(Path.cwd()) else Path("backups")
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_path(self, repo: GitRepository) -> Path:
        """Get the backup path for a repository.

        Creates a timestamped backup directory path under the repository's
        branch-specific backup location.

        Args:
            repo (GitRepository): Repository to get backup path for

        Returns:
            Path: Path where backup will be stored, formatted as:
                 backups/<repo_name>/<branch_name>/<timestamp>

        Note:
            In test mode, existing backups for the branch are cleaned up.
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_path = self.backup_dir / repo.name / repo.get_current_branch()

        # In test mode, clean up existing backups for this branch
        if "test_temp" in str(Path.cwd()) and branch_path.exists():
            shutil.rmtree(branch_path)

        path = branch_path / timestamp
        return path

    def get_program_paths(self, repo: GitRepository, program: str) -> Set[Path]:
        """Get all paths that would be backed up for Cursor IDE.

        Identifies all files and directories that should be backed up based on
        the configuration, supporting both exact paths and glob patterns.

        Args:
            repo (GitRepository): Repository to get paths from
            program (str): Program identifier (should be 'cursor')

        Returns:
            Set[Path]: Set of paths to back up, including both files and
                      directories that exist and have content

        Note:
            - Files in EXCLUDED_FILES are skipped
            - Empty files and directories are excluded
            - Glob patterns are supported for both files and directories
        """
        paths: Set[Path] = set()
        program_config = self.config.get_program_config(program)
        if not program_config:
            return paths

        for pattern in program_config.get("paths", []):
            pattern_path = Path(pattern)
            if "*" in str(pattern_path):
                # Handle glob patterns
                for matched_path in glob.glob(str(repo.path / pattern_path)):
                    path = Path(matched_path)
                    if path.exists():
                        if path.is_file() and path.stat().st_size > 0:
                            if path.name not in EXCLUDED_FILES:
                                paths.add(path)
                        elif path.is_dir():
                            for file_path in path.rglob("*"):
                                if (
                                    file_path.is_file()
                                    and file_path.stat().st_size > 0
                                    and file_path.name not in EXCLUDED_FILES
                                ):
                                    paths.add(file_path)
            else:
                # Handle exact paths
                path = repo.path / pattern_path
                if path.exists():
                    if path.is_file() and path.stat().st_size > 0:
                        if path.name not in EXCLUDED_FILES:
                            paths.add(path)
                    elif path.is_dir():
                        for file_path in path.rglob("*"):
                            if (
                                file_path.is_file()
                                and file_path.stat().st_size > 0
                                and file_path.name not in EXCLUDED_FILES
                            ):
                                paths.add(file_path)

        return paths

    def backup_program(
        self,
        repo: GitRepository,
        program: str,
        backup_path: Path,
        dry_run: bool = False,
    ) -> Tuple[bool, List[Path]]:
        """Backup Cursor IDE configuration files.

        Copies all configured Cursor IDE files and directories to the backup
        location, preserving their structure and metadata.

        Args:
            repo (GitRepository): Repository to backup from
            program (str): Program identifier (should be 'cursor')
            backup_path (Path): Base path for the backup
            dry_run (bool): If True, only show what would be backed up

        Returns:
            Tuple[bool, List[Path]]: (success, list of backed up paths)
                - success: True if any files were backed up
                - backed_up_paths: List of paths that were backed up

        Note:
            - Directories are copied recursively
            - File metadata is preserved using shutil.copy2
            - Empty files and directories are skipped
            - In dry-run mode, no files are actually copied
        """
        source_paths = self.get_program_paths(repo, program)
        if not source_paths:
            self.console.print(f"[yellow]No files found to backup for program '{program}'")
            return False, []

        backed_up_paths: List[Path] = []
        for path in sorted(list(source_paths)):
            if dry_run:
                self.console.print(f"[blue]Would backup: {path}")
                backed_up_paths.append(path)
                continue

            # Create destination path
            rel_path = path.relative_to(repo.path)
            dst_path = backup_path / rel_path
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            try:
                shutil.copy2(path, dst_path)
                backed_up_paths.append(path)
                self.console.print(f"[green]Backed up: {path}")
            except Exception as e:
                self.console.print(f"[red]Error backing up {path}: {e}")

        return bool(backed_up_paths), backed_up_paths

    def backup(
        self,
        repo: GitRepository | Path,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        dry_run: bool = False,
        zip_export: bool = False,
    ) -> bool:
        """Backup Cursor IDE configurations from a repository.

        Main entry point for backing up Cursor IDE configuration files. Handles
        the entire backup process including branch management and validation.

        Args:
            repo (GitRepository | Path): Repository or path to backup from
            programs (Optional[List[str]]): List of programs to backup. If None,
                                          backs up all configured programs
            branch (Optional[str]): Branch to backup from. If provided, switches
                                  to this branch before backup
            dry_run (bool): If True, only show what would be backed up
            zip_export (bool): If True, also create a zip archive of the backup

        Returns:
            bool: True if any files were backed up successfully

        Raises:
            ValueError: If source directory doesn't exist or isn't a directory

        Example:
            ```python
            manager = BackupManager(config)
            success = manager.backup(
                repo="/path/to/repo",
                branch="main",
                dry_run=True,
                zip_export=True
            )
            ```
        """
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

        # Get backup path but don't create it in dry run mode
        backup_path = self.backup_path(repo)
        self.console.print(f"[bold]Backup path: {backup_path}")

        # Create backup directory only if not in dry run mode
        if not dry_run:
            backup_path.mkdir(parents=True, exist_ok=True)

        backed_up = False
        backup_summary: Dict[str, Set[Path]] = {}

        # Backup each program
        for program in programs:
            success, backed_up_paths = self.backup_program(repo, program, backup_path, dry_run)
            if success:
                backed_up = True
                backup_summary[program] = set(backed_up_paths)

        if not backed_up:
            self.console.print("[yellow]Warning: No configurations were backed up")
            if not dry_run:
                # Clean up empty backup directory
                shutil.rmtree(backup_path)
            # For dry runs, return True if any program found files to back up
            if dry_run:
                for program in programs:
                    paths = self.get_program_paths(repo, program)
                    if paths:
                        return True
            return False

        if not dry_run:
            self.console.print(f"\nBackup created at {backup_path}\n")
            self.console.print("Backup Summary:")
            for program, paths in backup_summary.items():
                self.console.print(f"{program}:")
                for path in paths:
                    self.console.print(f"  - {path.relative_to(repo.path)}")

            # Create zip archive if requested
            if zip_export:
                zip_path = backup_path.with_suffix(".zip")
                self.console.print(f"\n[bold]Creating zip archive: {zip_path}")
                try:
                    exporter = ZipExporter(str(backup_path), str(zip_path))
                    exporter.export()
                    self.console.print(f"[green]Successfully created zip archive: {zip_path}")
                except Exception as e:
                    self.console.print(f"[red]Error creating zip archive: {e}")
                    # Don't fail the backup if zip creation fails
                    self.console.print("[yellow]Backup was successful but zip creation failed")

        return True

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

        # Structure:
        # backups/[repo]/[branch]/[timestamp]
        # We want to list all timestamp directories

        # If we're filtering by repo
        if repo:
            for branch_dir in backup_dir.iterdir():
                if branch_dir.is_dir():
                    for timestamp_dir in branch_dir.iterdir():
                        if timestamp_dir.is_dir():
                            backups.append(timestamp_dir)
        else:
            # List all repos
            for repo_dir in backup_dir.iterdir():
                if repo_dir.is_dir():
                    for branch_dir in repo_dir.iterdir():
                        if branch_dir.is_dir():
                            for timestamp_dir in branch_dir.iterdir():
                                if timestamp_dir.is_dir():
                                    backups.append(timestamp_dir)

        # Sort backups by timestamp (newest first)
        backups.sort(key=lambda x: x.name, reverse=True)
        return backups
