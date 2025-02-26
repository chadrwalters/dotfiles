"""Restore functionality for dotfiles."""

from __future__ import annotations

import filecmp
import logging
import shutil
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
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logging
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/dotfiles_debug.log"),
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
        logger.debug("RestoreManager initialized with backup directory: %s", self.backup_dir)

    def find_backup(
        self,
        repo_name: str,
        branch: Optional[str] = None,
        date: Optional[str] = None,
        latest: bool = False,
    ) -> Optional[Path]:
        """Find a backup for a repository.

        Args:
            repo_name: Name of the repository to find backups for.
            branch: Optional branch name to filter backups by.
            date: Optional date string (YYYYMMDD or YYYYMMDD-HHMMSS).
            latest: If True, return the latest backup regardless of date.

        Returns:
            Path to the backup directory if found, None otherwise.
        """
        # Ensure we're using an absolute path for the backup directory
        backup_dir = self.backup_dir
        logger.debug("Initial backup_dir: %s", backup_dir)
        logger.debug("Current working directory: %s", Path.cwd())

        if not backup_dir.is_absolute():
            # If we're in the dotfiles repository, use the relative path
            if Path.cwd().name == "dotfiles":
                backup_dir = Path.cwd() / backup_dir
                logger.debug("In dotfiles repo, updated backup_dir: %s", backup_dir)
            else:
                # Try to find the dotfiles repository
                dotfiles_path = Path.home() / "source" / "dotfiles"
                if dotfiles_path.exists():
                    backup_dir = dotfiles_path / backup_dir
                    logger.debug(
                        "Found dotfiles repo at %s, updated backup_dir: %s",
                        dotfiles_path,
                        backup_dir,
                    )
                else:
                    # Fall back to the current directory
                    backup_dir = Path.cwd() / backup_dir
                    logger.debug("Using current directory, updated backup_dir: %s", backup_dir)

        logger.debug("Final backup directory: %s", backup_dir)
        logger.debug("Checking if backup directory exists: %s", backup_dir.exists())

        if not backup_dir.exists():
            logger.warning("Backup directory %s does not exist", backup_dir)
            self.console.print(f"[yellow]Backup directory {backup_dir} does not exist[/yellow]")
            return None

        repo_dir = backup_dir / repo_name
        logger.debug("Repository directory: %s", repo_dir)
        logger.debug("Checking if repository directory exists: %s", repo_dir.exists())

        if not repo_dir.exists():
            logger.warning("No backups found for repository '%s'", repo_name)
            self.console.print(f"[yellow]No backups found for repository '{repo_name}'[/yellow]")
            return None

        # Get all backups for the repository
        backups = []

        # If branch specified, look in that branch directory
        if branch:
            branch_dir = repo_dir / branch
            logger.debug("Branch directory: %s", branch_dir)
            logger.debug("Checking if branch directory exists: %s", branch_dir.exists())

            if not branch_dir.exists():
                logger.warning("Branch directory %s does not exist", branch_dir)
                self.console.print(f"[yellow]No backups found for branch '{branch}'[/yellow]")
                return None
            backups = list(branch_dir.iterdir())
            logger.debug("Found %d backups in branch directory", len(backups))
        else:
            # Otherwise look in all branch directories
            logger.debug("No branch specified, looking in all branch directories")
            for branch_dir in repo_dir.iterdir():
                if branch_dir.is_dir():
                    logger.debug("Found branch directory: %s", branch_dir)
                    branch_backups = list(branch_dir.iterdir())
                    logger.debug(
                        "Found %d backups in branch directory %s", len(branch_backups), branch_dir
                    )
                    backups.extend(branch_backups)

        if not backups:
            logger.warning("No backups found for repository '%s'", repo_name)
            self.console.print(f"[yellow]No backups found for repository '{repo_name}'[/yellow]")
            return None

        # Sort backups by timestamp (newest first)
        backups.sort(key=lambda p: p.name, reverse=True)
        logger.debug("Found %d backups for repository '%s'", len(backups), repo_name)
        logger.debug("Backup paths: %s", [str(b) for b in backups])

        # If latest flag is set, return the latest backup
        if latest:
            logger.debug("Using latest backup: %s", backups[0])
            return backups[0]

        # If date is specified, find the matching backup
        if date:
            # Handle both full timestamp and date-only formats
            matching_backups = []
            for backup in backups:
                if date == backup.name:  # Exact match
                    logger.debug("Found exact date match: %s", backup)
                    return backup
                elif len(date) == 8 and backup.name.startswith(date):  # Date-only match
                    matching_backups.append(backup)

            if matching_backups:
                # Return the latest backup for the specified date
                latest_matching = max(matching_backups, key=lambda x: x.name)
                logger.debug("Found date match: %s", latest_matching)
                return latest_matching
            else:
                logger.warning("No backups found for date '%s'", date)
                self.console.print(f"[yellow]No backups found for date '{date}'[/yellow]")
                return None

        # Return latest backup if no date specified
        logger.debug("Using latest backup (default): %s", backups[0])
        return backups[0]

    def get_program_paths(self, repo: GitRepository, program: str) -> Set[Path]:
        """Get all paths that would be restored for a program."""
        paths: Set[Path] = set()
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
            source_dir: Source directory to restore from (backup directory).
            target_dir: Target directory to restore to.
            force: Whether to force restore over existing files.
            dry_run: Whether to perform a dry run.

        Returns:
            True if restore was successful, False otherwise.
        """
        if program not in self.config.programs:
            logger.warning("Program '%s' not found in configuration", program)
            self.console.print(f"[yellow]Program '{program}' not found in configuration[/yellow]")
            return False

        # The program directory is inside the source_dir (backup directory)
        program_dir = source_dir / program
        logger.debug("Looking for program directory at: %s", program_dir)

        if not program_dir.exists():
            logger.warning("Program directory '%s' not found in backup", program_dir)
            self.console.print(
                f"[yellow]Program directory '{program}' not found in backup at {source_dir}[/yellow]"
            )
            return False

        # Get program configuration
        program_config = self.config.get_program_config(program)
        if not program_config:
            logger.warning("No configuration found for program '%s'", program)
            self.console.print(f"[yellow]No configuration found for program '{program}'[/yellow]")
            return False

        files_restored = False
        logger.debug("Restoring program '%s' from %s to %s", program, program_dir, target_dir)

        # Clean up existing files if force is True
        if force and not dry_run:
            logger.debug("Force flag is set, cleaning up existing files for program '%s'", program)
            # First clean up directories
            for dir_pattern in program_config.get("directories", []):
                dir_path = target_dir / dir_pattern
                if dir_path.exists():
                    logger.debug("Removing directory: %s", dir_path)
                    shutil.rmtree(dir_path)

            # Then clean up files
            for file_pattern in program_config.get("files", []):
                file_path = target_dir / file_pattern
                if file_path.exists():
                    logger.debug("Removing file: %s", file_path)
                    file_path.unlink()

        # Restore files
        for file_pattern in program_config.get("files", []):
            src_path = program_dir / Path(file_pattern).name
            logger.debug("Checking for file: %s", src_path)
            if src_path.exists() and src_path.is_file():
                dst_path = target_dir / file_pattern
                logger.debug("Restoring file: %s -> %s", src_path, dst_path)
                if dst_path.exists() and not force:
                    logger.warning(
                        "Skipping existing file: %s (use --force to overwrite)", dst_path
                    )
                    self.console.print(
                        f"[yellow]Skipping existing file: {dst_path.relative_to(target_dir)} (use --force to overwrite)[/yellow]"
                    )
                    continue
                if dry_run:
                    self.console.print(
                        f"[blue]Would restore: {src_path.relative_to(source_dir)} -> {dst_path.relative_to(target_dir)}[/blue]"
                    )
                else:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src_path, dst_path)
                        logger.info("Successfully restored file: %s", dst_path)
                        self.console.print(
                            f"[green]Restored: {src_path.relative_to(source_dir)} -> {dst_path.relative_to(target_dir)}[/green]"
                        )
                        files_restored = True
                    except Exception as e:
                        logger.error("Failed to restore file %s: %s", dst_path, e)
                        self.console.print(f"[red]Failed to restore {dst_path}: {e}[/red]")

        # Restore directories
        for dir_pattern in program_config.get("directories", []):
            src_path = program_dir / Path(dir_pattern).name
            logger.debug("Checking for directory: %s", src_path)
            if src_path.exists() and src_path.is_dir():
                dst_path = target_dir / dir_pattern
                logger.debug("Restoring directory: %s -> %s", src_path, dst_path)
                if dst_path.exists() and not force:
                    logger.warning(
                        "Skipping existing directory: %s (use --force to overwrite)", dst_path
                    )
                    self.console.print(
                        f"[yellow]Skipping existing directory: {dst_path.relative_to(target_dir)} (use --force to overwrite)[/yellow]"
                    )
                    continue
                if dry_run:
                    self.console.print(
                        f"[blue]Would restore directory: {src_path.relative_to(source_dir)} -> {dst_path.relative_to(target_dir)}[/blue]"
                    )
                else:
                    if dst_path.exists():
                        logger.debug("Removing existing directory: %s", dst_path)
                        shutil.rmtree(dst_path)
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copytree(src_path, dst_path)
                        logger.info("Successfully restored directory: %s", dst_path)
                        self.console.print(
                            f"[green]Restored directory: {src_path.relative_to(source_dir)} -> {dst_path.relative_to(target_dir)}[/green]"
                        )
                        files_restored = True
                    except Exception as e:
                        logger.error("Failed to restore directory %s: %s", dst_path, e)
                        self.console.print(
                            f"[red]Failed to restore directory {dst_path}: {e}[/red]"
                        )

        if files_restored:
            logger.info("Successfully restored program '%s'", program)
        else:
            logger.warning("No files were restored for program '%s'", program)

        # For dry runs, we should return True even if no files were restored
        # since we're just showing what would be restored
        if dry_run:
            return True

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
                dst_path = target_dir / file_pattern

                # Check if the file exists in the backup
                if not src_path.exists() or not src_path.is_file():
                    # If the file doesn't exist in the backup but exists in the target,
                    # it's not a validation error (it wasn't restored)
                    if dst_path.exists():
                        # This is a file that was manually created or not removed during restore
                        logger.warning("File exists in target but not in backup: %s", dst_path)
                    continue

                # Now check if the file exists in the target
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
                dst_path = target_dir / dir_pattern

                # Check if the directory exists in the backup
                if not src_path.exists() or not src_path.is_dir():
                    # If the directory doesn't exist in the backup but exists in the target,
                    # it's not a validation error (it wasn't restored)
                    if dst_path.exists():
                        logger.warning("Directory exists in target but not in backup: %s", dst_path)
                    continue

                # Now check if the directory exists in the target
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
                        reason.append(f"Different files: {', '.join(comparison.diff_files[:3])}")
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
        repo_name: str,
        target_dir: Path,
        programs: Optional[List[str]] = None,
        branch: Optional[str] = None,
        date: Optional[str] = None,
        latest: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Restore program configurations.

        Args:
            repo_name: Repository name to restore from.
            target_dir: Target directory to restore to.
            programs: Optional list of programs to restore.
            branch: Optional branch to restore from.
            date: Optional date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS).
            latest: Whether to use the latest backup regardless of date.
            force: Whether to force restore over existing files.
            dry_run: Whether to perform a dry run.

        Returns:
            True if restore was successful, False otherwise.
        """
        logger.debug(
            "Restore called with repo_name=%s, target_dir=%s, programs=%s, branch=%s, date=%s, latest=%s, force=%s, dry_run=%s",
            repo_name,
            target_dir,
            programs,
            branch,
            date,
            latest,
            force,
            dry_run,
        )

        # Find the backup directory
        backup_path = self.find_backup(repo_name, branch, date, latest)
        if not backup_path:
            logger.warning("No backup found for repository '%s'", repo_name)
            return False

        logger.debug("Found backup at %s", backup_path)

        # Validate programs if specified
        if programs:
            for program in programs:
                if program not in self.config.programs:
                    logger.warning("Program '%s' not found in configuration", program)
                    self.console.print(
                        f"[yellow]Program '{program}' not found in configuration[/yellow]"
                    )
                    return False

                # Check if program exists in backup
                program_dir = backup_path / program
                if not program_dir.exists():
                    logger.warning("Program '%s' not found in backup at %s", program, backup_path)
                    self.console.print(f"[yellow]Program '{program}' not found in backup[/yellow]")
                    return False
        else:
            # If no programs specified, use all available in the backup
            programs = []
            for program_dir in backup_path.iterdir():
                if program_dir.is_dir() and program_dir.name in self.config.programs:
                    programs.append(program_dir.name)

            if not programs:
                logger.warning("No programs found in backup to restore")
                self.console.print("[yellow]No programs found in backup to restore[/yellow]")
                return False

        logger.debug("Programs to restore: %s", programs)

        # Create target directory if it doesn't exist
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Git repository for target directory
        repo = GitRepository(target_dir)

        # Restore each program
        any_restored = False
        files_skipped = False
        for program in programs:
            with self.console.status(f"Restoring {program} configurations..."):
                result = self.restore_program(program, backup_path, target_dir, force, dry_run)
                if result:
                    any_restored = True
                else:
                    # Check if files were skipped (existing files not overwritten)
                    program_config = self.config.get_program_config(program)
                    program_dir = backup_path / program
                    if program_dir.exists() and program_config:
                        for file_pattern in program_config.get("files", []):
                            src_path = program_dir / Path(file_pattern).name
                            dst_path = target_dir / file_pattern
                            if src_path.exists() and dst_path.exists() and not force:
                                files_skipped = True
                                break

                        if not files_skipped:
                            for dir_pattern in program_config.get("directories", []):
                                src_path = program_dir / Path(dir_pattern).name
                                dst_path = target_dir / dir_pattern
                                if src_path.exists() and dst_path.exists() and not force:
                                    files_skipped = True
                                    break

        if not any_restored and not files_skipped:
            logger.warning("No files were restored")
            self.console.print("[yellow]No files were restored[/yellow]")
            # For dry runs, we should return True even if no files were restored
            # since we're just showing what would be restored
            if dry_run:
                return True
            return False

        if not dry_run:
            if any_restored:
                self.console.print(f"[green]Restored files to {target_dir}[/green]")
            elif files_skipped:
                self.console.print(
                    f"[yellow]No files were restored to {target_dir} (files were skipped)[/yellow]"
                )

            # Validate the restore
            self.console.print("\nValidating restore...")
            is_valid, validation_results = self.validate_restore(backup_path, target_dir, programs)
            self.display_validation_results(validation_results)

            if not is_valid:
                self.console.print(
                    "[yellow]Warning: Some files may not have been restored correctly[/yellow]"
                )
            else:
                self.console.print("[green]All files restored successfully![/green]")

        # Return True if any files were restored or if files were skipped due to modifications
        return True if any_restored or files_skipped or dry_run else False
