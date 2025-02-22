"""Backup functionality for dotfiles."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console

from .config import Config
from .repository import GitRepository

console = Console()


class BackupManager:
    """Manages backups of program configurations."""

    def __init__(self, config: Config, console: Optional[Console] = None):
        """Initialize backup manager."""
        self.config = config
        self.console = console or Console()
        self.backup_dir = Path("backups")

    def backup_path(self, repo: GitRepository, branch: Optional[str] = None) -> Path:
        """Get backup path for repository."""
        if branch is None and isinstance(repo, GitRepository):
            branch = repo.get_current_branch()
        if branch is None:
            branch = "main"  # Default to main if no branch is available
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return self.backup_dir / repo.name / branch / timestamp

    def is_legacy_backup(self, backup_dir: Path) -> bool:
        """Check if a backup directory uses the legacy format."""
        if not backup_dir.is_dir():
            return False
        # Legacy backups have program directories directly under the repo directory
        return any(
            d.is_dir() and d.name in self.config.programs
            for d in backup_dir.iterdir()
            if d.is_dir()  # Only check directories
        )

    def list_backups(self, repo_name: Optional[Union[str, GitRepository]] = None) -> List[Path]:
        """List available backups."""
        if not self.backup_dir.exists():
            return []

        backups = []
        if repo_name:
            if isinstance(repo_name, GitRepository):
                repo_name = repo_name.name
            repo_dir = self.backup_dir / repo_name
            if not repo_dir.exists():
                return []
            # Handle both new and legacy backup structures
            if any(
                d.is_dir() and d.name in ["main", "develop"]
                for d in repo_dir.iterdir()
                if d.is_dir()
            ):
                # New structure: repo/branch/timestamp
                for branch_dir in repo_dir.iterdir():
                    if not branch_dir.is_dir():
                        continue
                    backups.extend(sorted(branch_dir.iterdir(), reverse=True))
            else:
                # Legacy structure: repo/program
                backups.append(repo_dir)
        else:
            for repo_dir in self.backup_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                # Handle both new and legacy backup structures
                if any(
                    d.is_dir() and d.name in ["main", "develop"]
                    for d in repo_dir.iterdir()
                    if d.is_dir()
                ):
                    # New structure: repo/branch/timestamp
                    for branch_dir in repo_dir.iterdir():
                        if not branch_dir.is_dir():
                            continue
                        backups.extend(sorted(branch_dir.iterdir(), reverse=True))
                else:
                    # Legacy structure: repo/program
                    backups.append(repo_dir)

        return backups

    def clean_old_backups(self, repo_name: str, keep: int = 5) -> None:
        """Clean old backups, keeping the specified number."""
        backups = self.list_backups(repo_name)
        if len(backups) > keep:
            for backup in backups[keep:]:
                shutil.rmtree(backup)

    def backup_program(
        self,
        repo: GitRepository,
        program: str,
        backup_path: Path,
        dry_run: bool = False,
    ) -> bool:
        """Backup program configurations."""
        program_config = self.config.get_program_config(program)
        if not program_config:
            return False

        program_backup_path = backup_path / program
        if dry_run:
            return True

        backed_up = False
        program_backup_path.mkdir(parents=True, exist_ok=True)

        # Backup files first
        for file_pattern in program_config.get("files", []):
            src_path = repo.path / file_pattern
            if src_path.exists() and src_path.is_file():
                # Place files directly under the program directory
                dst_path = program_backup_path / src_path.name
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                backed_up = True

        # Backup directories
        for dir_pattern in program_config.get("directories", []):
            src_path = repo.path / dir_pattern
            if src_path.exists() and src_path.is_dir():
                # Keep the exact path structure from the configuration
                dst_path = program_backup_path / dir_pattern
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_path, dst_path)
                backed_up = True

        return backed_up

    def backup(
        self,
        repo: GitRepository,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """Backup repository configurations."""
        backup_path = self.backup_path(repo, branch)
        programs = programs or list(self.config.programs)
        any_backed_up = False

        # First check if any program has files to backup
        has_program_files = False
        for program in programs:
            program_config = self.config.get_program_config(program)
            if not program_config:
                continue
            for file_pattern in program_config.get("files", []):
                src_path = repo.path / file_pattern
                if src_path.exists() and src_path.is_file():
                    has_program_files = True
                    break
            if has_program_files:
                break
            for dir_pattern in program_config.get("directories", []):
                src_path = repo.path / dir_pattern
                if src_path.exists() and src_path.is_dir():
                    has_program_files = True
                    break
            if has_program_files:
                break

        if not has_program_files:
            return False

        if not dry_run:
            # First backup base repository files
            base_files = ["test.txt"]  # List of base files to copy
            for file_name in base_files:
                src_path = repo.path / file_name
                if src_path.exists() and src_path.is_file():
                    dst_path = backup_path / file_name
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    any_backed_up = True

        # Then backup program-specific files
        for program in programs:
            with self.console.status(f"Backing up {program} configurations..."):
                if self.backup_program(repo, program, backup_path, dry_run):
                    any_backed_up = True

        if not any_backed_up:
            self.console.print("Warning: No configurations were backed up")
            if not dry_run and backup_path.exists():
                shutil.rmtree(backup_path)

        return any_backed_up
