"""Restore functionality for dotfiles."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from .backup import BackupManager
from .config import Config
from .repository import GitRepository

console = Console()


class RestoreManager:
    """Manages restoring configurations from backups."""

    def __init__(self, config: Config, backup_manager: BackupManager) -> None:
        """Initialize the restore manager."""
        self.config = config
        self.backup_manager = backup_manager
        self.console = Console()

    def find_backup(
        self,
        repo_name: str,
        branch: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[Path]:
        """Find most recent backup for repository and branch."""
        backups = self.backup_manager.list_backups(repo_name)
        if not backups:
            return None

        # Filter by branch if specified
        if branch:
            backups = [b for b in backups if b.parent.name == branch]
            if not backups:
                return None

        # Filter by timestamp if specified
        if timestamp:
            backups = [b for b in backups if b.name == timestamp]
            if not backups:
                return None

        # Return most recent backup
        return backups[-1]

    def check_conflicts(
        self,
        repo: GitRepository,
        backup_path: Path,
        program: Optional[str] = None,
    ) -> List[Tuple[Path, Path]]:
        """Check for conflicts between backup and repository."""
        conflicts = []
        programs = [program] if program else self.config.programs

        for prog_name in programs:
            prog_config = self.config.get_program_config(prog_name)
            if not prog_config:
                continue

            prog_backup = backup_path / prog_name
            if not prog_backup.exists():
                continue

            # Check files
            for file_pattern in prog_config["files"]:
                backup_file = prog_backup / Path(file_pattern).name
                repo_file = repo.path / file_pattern
                if (
                    backup_file.exists()
                    and backup_file.is_file()
                    and repo_file.exists()
                    and repo_file.is_file()
                ):
                    conflicts.append((backup_file, repo_file))

            # Check directories
            for dir_pattern in prog_config["directories"]:
                backup_dir = prog_backup / dir_pattern
                repo_dir = repo.path / dir_pattern
                if (
                    backup_dir.exists()
                    and backup_dir.is_dir()
                    and repo_dir.exists()
                    and repo_dir.is_dir()
                ):
                    conflicts.append((backup_dir, repo_dir))

        return conflicts

    def restore(
        self,
        repo: GitRepository,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> bool:
        """Restore configurations."""
        success = True
        restored = False

        # Get list of programs to restore
        if programs is None:
            programs = list(self.config.programs.keys())

        # Find most recent backup
        backup_path = None
        backups = self.backup_manager.list_backups(repo.name)
        if backups:
            if branch:
                branch_backups = [b for b in backups if b.parent.name == branch]
                if branch_backups:
                    backup_path = branch_backups[-1]  # Get most recent
            else:
                backup_path = backups[-1]  # Get most recent

        if not backup_path:
            self.console.print("No suitable backup found")
            return False

        # Check for conflicts first
        if not dry_run:
            conflicts = []
            for program in programs:
                program_conflicts = self.check_conflicts(repo, backup_path, program)
                conflicts.extend(program_conflicts)
            if conflicts and not force:
                self.console.print("[red]Conflicts found. Use --force to overwrite.")
                return False

        # Clean up files from other programs if restoring specific programs
        if not dry_run and programs != list(self.config.programs.keys()):
            for program_name in self.config.programs:
                if program_name not in programs:
                    config = self.config.get_program_config(program_name)
                    if not config:
                        continue

                    # Clean up files
                    for file_pattern in config.get("files", []):
                        file_path = repo.path / file_pattern
                        if file_path.exists() and file_path.is_file():
                            file_path.unlink()

                    # Clean up directories
                    for dir_pattern in config.get("directories", []):
                        dir_path = repo.path / dir_pattern
                        if dir_path.exists() and dir_path.is_dir():
                            shutil.rmtree(dir_path)

        with Live(Spinner("dots"), refresh_per_second=10) as live:
            for program in programs:
                program_config = self.config.get_program_config(program)
                if not program_config:
                    continue

                # Cast program_config to Dict[str, Any] since we've checked it's not None
                program_config = cast(Dict[str, Any], program_config)

                live.update(Spinner("dots", f"Restoring {program} configurations..."))

                try:
                    program_dir = backup_path / program
                    if not program_dir.exists():
                        continue

                    # Get files to restore
                    for file_pattern in program_config.get("files", []):
                        file_path = program_dir / Path(file_pattern).name
                        if file_path.exists() and file_path.is_file():
                            dst = repo.path / file_pattern
                            if dst.exists():
                                if not force and not dry_run:
                                    self.console.print(f"Skipping {file_pattern} (already exists)")
                                    continue
                                elif not dry_run:
                                    if dst.is_dir():
                                        shutil.rmtree(dst)
                                    else:
                                        dst.unlink()
                                else:
                                    self.console.print(f"Would overwrite {file_pattern}")

                            if not dry_run:
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(file_path, dst)
                                restored = True
                            else:
                                self.console.print(f"Would restore {file_pattern}")
                                restored = True

                    # Get directories to restore
                    for dir_pattern in program_config.get("directories", []):
                        dir_path = program_dir / dir_pattern
                        if dir_path.exists() and dir_path.is_dir():
                            dst = repo.path / dir_pattern
                            if dst.exists():
                                if not force and not dry_run:
                                    self.console.print(f"Skipping {dir_pattern} (already exists)")
                                    continue
                                elif not dry_run:
                                    shutil.rmtree(dst)
                                else:
                                    self.console.print(f"Would overwrite {dir_pattern}")

                            if not dry_run:
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copytree(dir_path, dst)
                                restored = True
                            else:
                                self.console.print(f"Would restore {dir_pattern}")
                                restored = True

                except Exception as e:
                    self.console.print(f"[red]Error restoring {program}: {e}")
                    success = False

        if not restored:
            self.console.print("[yellow]Warning: No configurations were restored")
            return False

        return success and restored
