"""Restore functionality for dotfiles."""

from __future__ import annotations

import filecmp
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.table import Table

from .backup import BackupManager
from .config import Config
from .repository import GitRepository

console = Console()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("dotfiles_restore.log"),
        logging.StreamHandler(),
    ],
)


class RestoreManager:
    """Manage restoring program configurations."""

    def __init__(self, config: Config, backup_manager: BackupManager) -> None:
        """Initialize restore manager.

        Args:
            config: Program configuration.
            backup_manager: Backup manager instance.
        """
        self.config = config
        self.backup_manager = backup_manager
        self.console = Console()
        self.backup_dir = (
            Path("test_temp/backups") if "test_temp" in str(Path.cwd()) else Path("backups")
        )
        logger.info("RestoreManager initialized with backup directory: %s", self.backup_dir)

    def find_backup(self, repo_name: str, branch: Optional[str] = None) -> Optional[Path]:
        """Find the latest backup for a repository."""
        if not self.backup_dir.exists():
            return None

        repo_dir = self.backup_dir / repo_name
        if not repo_dir.exists():
            return None

        # If branch specified, look in that branch directory
        if branch:
            branch_dir = repo_dir / branch
            if not branch_dir.exists():
                return None
            backups = list(branch_dir.iterdir())
        else:
            # Otherwise look in all branch directories
            backups = []
            for branch_dir in repo_dir.iterdir():
                if branch_dir.is_dir():
                    backups.extend(branch_dir.iterdir())

        if not backups:
            return None

        # Return latest backup based on timestamp
        return max(backups, key=lambda p: datetime.strptime(p.name, "%Y%m%d-%H%M%S"))

    def get_program_paths(self, repo: GitRepository, program: str) -> Set[Path]:
        """Get all paths that would be restored for a program."""
        paths = set()
        program_config = self.config.get_program_config(program)
        if not program_config:
            return paths

        # Get paths to restore
        files = program_config.get("files", [])
        directories = program_config.get("directories", [])

        # Add file paths
        for file_pattern in files:
            file_path = repo.path / file_pattern
            paths.add(file_path)

        # Add directory paths
        for dir_pattern in directories:
            dir_path = repo.path / dir_pattern
            paths.add(dir_path)

        return paths

    def check_conflicts(self, repo: GitRepository, backup_path: Path) -> Set[Tuple[Path, Path]]:
        """Check for conflicts between backup and target directory."""
        conflicts = set()

        for program in self.config.programs:
            program_config = self.config.get_program_config(program)
            if not program_config:
                continue

            program_backup = backup_path / program
            if not program_backup.exists():
                continue

            # Get all paths that would be restored
            target_paths = self.get_program_paths(repo, program)

            # Check each target path for conflicts
            for target_path in target_paths:
                if target_path.exists():
                    # Get the corresponding backup path
                    rel_path = target_path.relative_to(repo.path)
                    backup_file = program_backup / rel_path.name
                    if backup_file.exists():
                        conflicts.add((target_path, backup_file))

        return conflicts

    def restore_program(
        self,
        program: str,
        source_dir: Path,
        target_dir: Path,
        force: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Restore program configurations.

        Args:
            program: Program to restore.
            source_dir: Source directory to restore from.
            target_dir: Target directory to restore to.
            force: Whether to force restore over existing files.
            dry_run: Whether to perform a dry run.

        Returns:
            True if restore was successful, False otherwise.
        """
        if program not in self.config.programs:
            logger.warning("Program '%s' not found in configuration", program)
            return False

        program_dir = source_dir / program
        if not program_dir.exists():
            logger.warning("Program directory '%s' not found in backup", program_dir)
            return False

        # Get program configuration
        program_config = self.config.get_program_config(program)
        if not program_config:
            logger.warning("No configuration found for program '%s'", program)
            return False

        files_restored = False
        logger.info("Restoring program '%s' from %s to %s", program, source_dir, target_dir)

        # Clean up existing files if force is True
        if force and not dry_run:
            logger.info("Force flag is set, cleaning up existing files for program '%s'", program)
            # First clean up directories
            for dir_pattern in program_config.get("directories", []):
                dir_path = target_dir / dir_pattern
                if dir_path.exists():
                    logger.info("Removing directory: %s", dir_path)
                    shutil.rmtree(dir_path)

            # Then clean up files
            for file_pattern in program_config.get("files", []):
                file_path = target_dir / file_pattern
                if file_path.exists():
                    logger.info("Removing file: %s", file_path)
                    file_path.unlink()

        # Restore files
        for file_pattern in program_config.get("files", []):
            src_path = program_dir / Path(file_pattern).name
            if src_path.exists() and src_path.is_file():
                dst_path = target_dir / file_pattern
                logger.info("Restoring file: %s -> %s", src_path, dst_path)
                if not dry_run:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src_path, dst_path)
                        logger.info("Successfully restored file: %s", dst_path)
                    except Exception as e:
                        logger.error("Failed to restore file %s: %s", dst_path, e)
                files_restored = True

        # Restore directories
        for dir_pattern in program_config.get("directories", []):
            src_path = program_dir / Path(dir_pattern).name
            if src_path.exists() and src_path.is_dir():
                dst_path = target_dir / dir_pattern
                logger.info("Restoring directory: %s -> %s", src_path, dst_path)
                if not dry_run:
                    if dst_path.exists():
                        logger.info("Removing existing directory: %s", dst_path)
                        shutil.rmtree(dst_path)
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copytree(src_path, dst_path)
                        logger.info("Successfully restored directory: %s", dst_path)
                    except Exception as e:
                        logger.error("Failed to restore directory %s: %s", dst_path, e)
                files_restored = True

        if files_restored:
            logger.info("Successfully restored program '%s'", program)
        else:
            logger.warning("No files were restored for program '%s'", program)

        return files_restored

    def validate_restore(
        self,
        backup_path: Path,
        target_dir: Path,
        programs: List[str],
    ) -> Tuple[bool, Dict[str, Dict[str, List[Tuple[Path, Optional[str]]]]]]:
        """Validate that files were restored correctly.

        Args:
            backup_path: Path to backup directory.
            target_dir: Path to target directory.
            programs: List of programs to validate.

        Returns:
            Tuple of (success, validation_results).
            validation_results is a dict with program names as keys and a dict with
            'success' and 'failed' lists of paths as values. Failed entries include
            the reason for failure.
        """
        logger.info("Validating restore from %s to %s", backup_path, target_dir)
        validation_results: Dict[str, Dict[str, List[Tuple[Path, Optional[str]]]]] = {}
        all_valid = True

        for program in programs:
            program_config = self.config.get_program_config(program)
            if not program_config:
                logger.warning("No configuration found for program '%s'", program)
                continue

            program_dir = backup_path / program
            if not program_dir.exists():
                logger.warning("Program directory '%s' not found in backup", program_dir)
                continue

            validation_results[program] = {"success": [], "failed": []}
            logger.info("Validating program '%s'", program)

            # Validate files
            for file_pattern in program_config.get("files", []):
                src_path = program_dir / Path(file_pattern).name
                if src_path.exists() and src_path.is_file():
                    dst_path = target_dir / file_pattern
                    if not dst_path.exists():
                        all_valid = False
                        logger.error("File does not exist in target: %s", dst_path)
                        validation_results[program]["failed"].append(
                            (dst_path, "File does not exist in target")
                        )
                        continue

                    # Compare file contents
                    if filecmp.cmp(src_path, dst_path, shallow=False):
                        logger.info("File validated successfully: %s", dst_path)
                        validation_results[program]["success"].append((dst_path, None))
                    else:
                        all_valid = False
                        # Get file sizes for additional info
                        src_size = src_path.stat().st_size
                        dst_size = dst_path.stat().st_size
                        logger.error(
                            "File content mismatch: %s (backup: %d bytes, target: %d bytes)",
                            dst_path,
                            src_size,
                            dst_size,
                        )
                        validation_results[program]["failed"].append(
                            (
                                dst_path,
                                f"Content mismatch (backup: {src_size} bytes, target: {dst_size} bytes)",
                            )
                        )

            # Validate directories
            for dir_pattern in program_config.get("directories", []):
                src_path = program_dir / Path(dir_pattern).name
                if src_path.exists() and src_path.is_dir():
                    dst_path = target_dir / dir_pattern
                    if not dst_path.exists():
                        all_valid = False
                        logger.error("Directory does not exist in target: %s", dst_path)
                        validation_results[program]["failed"].append(
                            (dst_path, "Directory does not exist in target")
                        )
                        continue

                    # Compare directory contents
                    comparison = filecmp.dircmp(src_path, dst_path)
                    if (
                        not comparison.diff_files
                        and not comparison.left_only
                        and not comparison.right_only
                    ):
                        logger.info("Directory validated successfully: %s", dst_path)
                        validation_results[program]["success"].append((dst_path, None))
                    else:
                        all_valid = False
                        reason = []
                        if comparison.diff_files:
                            reason.append(
                                f"Different files: {', '.join(comparison.diff_files[:3])}"
                            )
                            if len(comparison.diff_files) > 3:
                                reason[-1] += " and more"
                            logger.error(
                                "Directory has different files: %s - %s",
                                dst_path,
                                ", ".join(comparison.diff_files[:3]),
                            )
                        if comparison.left_only:
                            reason.append(
                                f"Files only in backup: {', '.join(comparison.left_only[:3])}"
                            )
                            if len(comparison.left_only) > 3:
                                reason[-1] += " and more"
                            logger.error(
                                "Directory missing files from backup: %s - %s",
                                dst_path,
                                ", ".join(comparison.left_only[:3]),
                            )
                        if comparison.right_only:
                            reason.append(
                                f"Files only in target: {', '.join(comparison.right_only[:3])}"
                            )
                            if len(comparison.right_only) > 3:
                                reason[-1] += " and more"
                            logger.error(
                                "Directory has extra files not in backup: %s - %s",
                                dst_path,
                                ", ".join(comparison.right_only[:3]),
                            )
                        validation_results[program]["failed"].append((dst_path, "; ".join(reason)))

        if all_valid:
            logger.info("All files validated successfully")
        else:
            logger.warning("Some files failed validation")

        return all_valid, validation_results

    def display_validation_results(
        self,
        validation_results: Dict[str, Dict[str, List[Tuple[Path, Optional[str]]]]],
    ) -> None:
        """Display validation results in a table.

        Args:
            validation_results: Validation results from validate_restore.
        """
        table = Table(title="Restore Validation Results")
        table.add_column("Program", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        for program, results in validation_results.items():
            success_count = len(results["success"])
            failed_count = len(results["failed"])
            total_count = success_count + failed_count

            if failed_count == 0:
                status = "[green]✓ Success[/green]"
                details = f"All {total_count} files restored correctly"
            else:
                status = "[red]✗ Failed[/red]"
                details = f"{success_count}/{total_count} files restored correctly"

                # Add failed files to details with reasons
                if failed_count > 0:
                    failed_details = []
                    for path, reason in results["failed"][:3]:
                        rel_path = path.relative_to(path.parent.parent)
                        failed_details.append(f"{rel_path}: {reason}" if reason else str(rel_path))

                    if len(results["failed"]) > 3:
                        failed_details.append("...")

                    details += "\nFailed files:\n- " + "\n- ".join(failed_details)

            table.add_row(program, status, details)

        self.console.print(table)

    def restore(
        self,
        repo: GitRepository,
        target_dir: Optional[Path] = None,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Restore program configurations.

        Args:
            repo: Git repository to restore to.
            target_dir: Optional target directory to restore to.
            programs: Optional list of programs to restore.
            branch: Optional branch to restore from.
            force: Whether to force restore over existing files.
            dry_run: Whether to perform a dry run.

        Returns:
            True if restore was successful, False otherwise.
        """
        if not target_dir:
            target_dir = repo.path

        # Find latest backup
        backups = self.backup_manager.list_backups(repo.name)
        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            return False

        backup_path = backups[-1]
        if branch:
            # Find latest backup for branch
            branch_backups = [b for b in backups if b.parent.name == branch]
            if not branch_backups:
                console.print(f"[yellow]No backups found for branch {branch}[/yellow]")
                return False
            backup_path = branch_backups[-1]

        # Check for conflicts
        if not force and not dry_run:
            conflicts = self.check_conflicts(repo, backup_path)
            if conflicts:
                console.print("[yellow]Conflicts found:[/yellow]")
                for conflict in conflicts:
                    console.print(f"  {conflict}")
                return False

        # Create target directory if it doesn't exist
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        # Get list of programs to restore
        if not programs:
            programs = list(self.config.programs.keys())
        else:
            # Validate programs
            invalid_programs = [p for p in programs if p not in self.config.programs]
            if invalid_programs:
                console.print(f"[yellow]Invalid programs: {', '.join(invalid_programs)}[/yellow]")
                return False

        # Clean up target directory before restoring
        if force and not dry_run:
            # Only clean up directories for the programs being restored
            for program in programs:
                program_config = self.config.get_program_config(program)
                if not program_config:
                    continue
                program_dir = backup_path / program
                if not program_dir.exists():
                    continue

                # Clean up directories
                for dir_pattern in program_config.get("directories", []):
                    dir_path = target_dir / dir_pattern
                    if dir_path.exists():
                        shutil.rmtree(dir_path)

                # Clean up files
                for file_pattern in program_config.get("files", []):
                    file_path = target_dir / file_pattern
                    if file_path.exists():
                        file_path.unlink()

        # Restore each program
        any_restored = False
        for program in programs:
            with console.status(f"Restoring {program} configurations..."):
                if self.restore_program(program, backup_path, target_dir, force, dry_run):
                    any_restored = True

        if not any_restored:
            console.print("[yellow]No files were restored[/yellow]")
            return False

        if not dry_run:
            console.print(f"Restored files to {target_dir}")

            # Validate the restore
            console.print("\nValidating restore...")
            is_valid, validation_results = self.validate_restore(backup_path, target_dir, programs)
            self.display_validation_results(validation_results)

            if not is_valid:
                console.print(
                    "[yellow]Warning: Some files may not have been restored correctly[/yellow]"
                )
            else:
                console.print("[green]All files restored successfully![/green]")

        return True
