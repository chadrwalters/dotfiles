"""Migration functionality for dotfiles."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .backup import BackupManager
from .config import Config


class MigrateManager:
    """Manages migration of legacy backups to new format."""

    def __init__(self, config: Config, console: Optional[Console] = None):
        """Initialize migrate manager."""
        self.config = config
        self.console = console or Console()
        self.backup_manager = BackupManager(config, console)

    def is_legacy_backup(self, backup_dir: Path) -> bool:
        """Check if a backup directory uses the legacy format."""
        if not backup_dir.is_dir():
            return False
        # Legacy backups have program directories directly under the repo directory
        return any(d.is_dir() and d.name in self.config.programs for d in backup_dir.iterdir())

    def get_legacy_backups(self) -> List[Path]:
        """Get list of legacy backup directories."""
        if not self.backup_manager.backup_dir.exists():
            return []
        return [
            d
            for d in self.backup_manager.backup_dir.iterdir()
            if d.is_dir() and self.is_legacy_backup(d) and not d.name.endswith(".legacy")
        ]

    def migrate_backup(
        self,
        legacy_backup: Path,
        branch: str = "main",
        dry_run: bool = False,
    ) -> Tuple[bool, Optional[Path]]:
        """Migrate a legacy backup to the new format."""
        # Create timestamp for the migrated backup
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        repo_name = legacy_backup.name.replace(".legacy", "")
        new_backup_path = self.backup_manager.backup_dir / repo_name / branch / timestamp

        if dry_run:
            return True, new_backup_path

        try:
            # Create the new backup directory structure
            new_backup_path.mkdir(parents=True, exist_ok=True)

            # Copy all program directories
            for program_dir in legacy_backup.iterdir():
                if program_dir.is_dir() and program_dir.name in self.config.programs:
                    shutil.copytree(
                        program_dir, new_backup_path / program_dir.name, dirs_exist_ok=True
                    )

            # Clean up any intermediate directories
            repo_dir = self.backup_manager.backup_dir / repo_name
            for item in repo_dir.iterdir():
                if item.is_dir() and item.name not in ["main", "develop"]:
                    shutil.rmtree(item)

            # Move the legacy backup to .legacy suffix only after successful copy
            legacy_path = legacy_backup.with_suffix(".legacy")
            if legacy_path != legacy_backup:  # Only rename if not already .legacy
                if legacy_path.exists():
                    shutil.rmtree(legacy_path)
                try:
                    legacy_backup.rename(legacy_path)
                except OSError:
                    # If rename fails, try copy and remove
                    shutil.copytree(legacy_backup, legacy_path)
                    shutil.rmtree(legacy_backup)

            return True, new_backup_path
        except Exception as e:
            self.console.print(f"[red]Error migrating {legacy_backup.name}: {e}[/]")
            if new_backup_path.exists():
                shutil.rmtree(new_backup_path)
            return False, None

    def migrate(
        self,
        repos: Optional[List[str]] = None,
        branch: str = "main",
        dry_run: bool = False,
    ) -> bool:
        """Migrate all legacy backups to new format."""
        legacy_backups = self.get_legacy_backups()
        if not legacy_backups:
            self.console.print("No legacy backups found.")
            return True

        if repos:
            legacy_backups = [b for b in legacy_backups if b.name in repos]
            if not legacy_backups:
                self.console.print("No legacy backups found for specified repositories.")
                return True

        success = True
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            for legacy_backup in progress.track(
                legacy_backups,
                description="Migrating backups...",
            ):
                self.console.print(f"\nMigrating {legacy_backup.name}...")
                migrated, new_path = self.migrate_backup(legacy_backup, branch, dry_run)
                if migrated:
                    self.console.print(
                        f"[green]Successfully migrated {legacy_backup.name} "
                        f"to new format at {new_path}[/]"
                    )
                else:
                    self.console.print(f"[red]Failed to migrate {legacy_backup.name}[/]")
                    success = False

        return success
