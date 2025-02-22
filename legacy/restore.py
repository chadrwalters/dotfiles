#!/usr/bin/env python3
"""Legacy restore functionality."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

import config
from config import BACKUP_DIR, get_program_dirs, get_program_files, get_sibling_repos

config_instance = config.Config()


def get_available_backups() -> List[Path]:
    """Get list of available backups."""
    backup_dir = Path(BACKUP_DIR)
    if not backup_dir.exists():
        return []
    return [d for d in backup_dir.iterdir() if d.is_dir()]


def select_backup(backups: List[Path]) -> Optional[Path]:
    """Let user select a backup to restore from."""
    print("\nAvailable backups:")
    for i, backup in enumerate(backups, 1):
        print(f"{i}. {backup.name}")

    while True:
        try:
            choice = input("\nSelect backup (or press Enter to cancel): ")
            if not choice:
                return None
            index = int(choice) - 1
            if 0 <= index < len(backups):
                return backups[index]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def select_target_repo(repos: List[Path]) -> Optional[Path]:
    """Let user select a repository to restore to."""
    print("\nAvailable repositories:")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo.name}")

    while True:
        try:
            choice = input("\nSelect repository (or press Enter to cancel): ")
            if not choice:
                return None
            index = int(choice) - 1
            if 0 <= index < len(repos):
                return repos[index]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def check_conflicts(target_repo: Path, program: str) -> List[str]:
    """Check for existing files that would be overwritten."""
    conflicts = []

    # Check files
    for file in get_program_files(program):
        if (target_repo / file).exists():
            conflicts.append(file)

    # Check directories
    for dir_name in get_program_dirs(program):
        if (target_repo / dir_name).exists():
            conflicts.append(dir_name)

    return conflicts


def restore_files(source_backup: Path, target_repo: Path, program: str) -> bool:
    """Restore files for a specific program."""
    success = True
    program_backup_dir = source_backup / program

    if not program_backup_dir.exists():
        print(f"No backup found for {program}")
        return False

    # Restore individual files
    for file in get_program_files(program):
        source_file = program_backup_dir / file
        if source_file.exists():
            try:
                restore_file(source_file, target_repo / file)
            except Exception as e:
                print(f"Error restoring {file}: {e}")
                success = False

    # Restore directories
    for dir_name in get_program_dirs(program):
        source_dir = program_backup_dir / dir_name
        if source_dir.exists():
            target_dir = target_repo / dir_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            try:
                restore_directory(source_dir, target_dir)
            except Exception as e:
                print(f"Error restoring directory {dir_name}: {e}")
                success = False

    return success


def restore_file(src: Path, dest: Path) -> None:
    """Restore a single file."""
    if not src.exists():
        print(f"Source file {src} does not exist")
        return

    # Create parent directory if it doesn't exist
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(src, dest)
    print(f"Restored {dest}")


def restore_directory(src: Path, dest: Path) -> None:
    """Restore a directory."""
    if not src.exists():
        print(f"Source directory {src} does not exist")
        return

    # Remove existing directory if it exists
    if dest.exists():
        shutil.rmtree(dest)

    # Copy directory
    shutil.copytree(src, dest)
    print(f"Restored {dest}")


def restore_program(program: str, backup_dir: Path, target_dir: Path) -> None:
    """Restore program files from backup."""
    # Restore individual files
    for file_path in get_program_files(program):
        src = backup_dir / file_path
        dest = target_dir / file_path
        if src.exists():
            restore_file(src, dest)

    # Restore directories
    for dir_path in get_program_dirs(program):
        src = backup_dir / dir_path
        dest = target_dir / dir_path
        if src.exists():
            restore_directory(src, dest)


def restore_backup(backup_dir: Path, target_dir: Path, programs: list[str] | None = None) -> None:
    """Restore files from backup."""
    if not backup_dir.exists():
        print(f"Backup directory {backup_dir} does not exist")
        return

    # Get list of programs to restore
    if programs is None:
        programs = []
        for item in backup_dir.iterdir():
            if item.is_file():
                programs.extend([p for p in get_program_files(item.name)])
            elif item.is_dir():
                programs.extend([p for p in get_program_dirs(item.name)])

    # Restore each program
    for program in programs:
        restore_program(program, backup_dir, target_dir)


def main() -> None:
    """Main function."""
    # Get available backups
    backups = get_available_backups()
    if not backups:
        print("No backups found.")
        return

    # Let user select backup
    source_backup = select_backup(backups)
    if not source_backup:
        return

    # Get available repositories
    repos = get_sibling_repos()
    if not repos:
        print("No Git repositories found.")
        return

    # Let user select target repository
    target_repo = select_target_repo(repos)
    if not target_repo:
        return

    # Get program to restore
    programs = config_instance.get_all_programs()
    if not programs:
        print("No programs configured.")
        return

    print("\nAvailable programs:")
    for i, program in enumerate(programs, 1):
        print(f"{i}. {config_instance.get_program_name(program)}")

    while True:
        try:
            choice = input("\nSelect program (or press Enter to cancel): ")
            if not choice:
                return
            index = int(choice) - 1
            if 0 <= index < len(programs):
                program = programs[index]
                break
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Check for conflicts
    conflicts = check_conflicts(target_repo, program)
    if conflicts:
        print("\nThe following files would be overwritten:")
        for conflict in conflicts:
            print(f"  {conflict}")

        response = input("\nDo you want to proceed? [y/N]: ")
        if response.lower() != "y":
            print("Restore cancelled.")
            return

    # Restore files
    success = restore_files(source_backup, target_repo, program)
    if success:
        print("\nRestore completed successfully.")
    else:
        print("\nRestore completed with some errors.")


if __name__ == "__main__":
    main()
