#!/usr/bin/env python3
"""Restore script for dotfiles."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import config

def get_available_backups() -> List[Path]:
    """Get list of repositories that have backups."""
    backup_dir = config.BACKUP_DIR
    if not backup_dir.exists():
        return []
    return [d for d in backup_dir.iterdir() if d.is_dir()]

def select_backup(backups: List[Path]) -> Optional[Path]:
    """Let user select a backup to restore from."""
    if not backups:
        print("No backups found!")
        return None

    print("\nAvailable backups:")
    for i, backup in enumerate(backups, 1):
        print(f"{i}. {backup.name}")

    while True:
        try:
            choice = int(input("\nSelect backup source [1-{}]: ".format(len(backups))))
            if 1 <= choice <= len(backups):
                return backups[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")

def get_sibling_repos() -> List[Path]:
    """Get list of sibling repositories."""
    current_dir = Path.cwd()
    parent_dir = current_dir.parent
    return [d for d in parent_dir.iterdir()
            if d.is_dir() and d != current_dir and (d / '.git').exists()]

def select_target_repo(repos: List[Path]) -> Optional[Path]:
    """Let user select a repository to restore to."""
    if not repos:
        print("No target repositories found!")
        return None

    print("\nTarget repositories:")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo.name}")

    while True:
        try:
            choice = int(input("\nSelect target repo [1-{}]: ".format(len(repos))))
            if 1 <= choice <= len(repos):
                return repos[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")

def check_conflicts(target_repo: Path, program: str) -> List[str]:
    """Check for existing files that would be overwritten."""
    conflicts = []

    # Check files
    for file in config.get_program_files(program):
        if (target_repo / file).exists():
            conflicts.append(file)

    # Check directories
    for dir_name in config.get_program_dirs(program):
        if (target_repo / dir_name).exists():
            conflicts.append(dir_name)

    return conflicts

def restore_files(source_backup: Path, target_repo: Path, program: str) -> bool:
    """Restore files for a specific program."""
    program_backup_dir = source_backup / program
    if not program_backup_dir.exists():
        print(f"No backup found for {config.get_program_name(program)}")
        return True

    success = True

    # Restore individual files
    for file in config.get_program_files(program):
        source_file = program_backup_dir / file
        if source_file.exists():
            try:
                shutil.copy2(source_file, target_repo / file)
                print(f"Restored: {file}")
            except Exception as e:
                print(f"Error restoring {file}: {e}")
                success = False

    # Restore directories
    for dir_name in config.get_program_dirs(program):
        source_dir = program_backup_dir / dir_name
        if source_dir.exists():
            target_dir = target_repo / dir_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            try:
                shutil.copytree(source_dir, target_dir)
                print(f"Restored directory: {dir_name}")
            except Exception as e:
                print(f"Error restoring directory {dir_name}: {e}")
                success = False

    return success

def main():
    """Main function."""
    backups = get_available_backups()
    source_backup = select_backup(backups)

    if not source_backup:
        return

    repos = get_sibling_repos()
    target_repo = select_target_repo(repos)

    if not target_repo:
        return

    # Check for conflicts
    all_conflicts = []
    for program in config.get_all_programs():
        conflicts = check_conflicts(target_repo, program)
        if conflicts:
            all_conflicts.extend(conflicts)

    if all_conflicts:
        print("\nWarning: The following files/directories will be overwritten:")
        for conflict in all_conflicts:
            print(f"- {conflict}")

        response = input("\nDo you want to proceed? [y/N]: ")
        if response.lower() != 'y':
            print("Restore cancelled.")
            return

    print(f"\nRestoring to: {target_repo.name}")

    all_success = True
    for program in config.get_all_programs():
        print(f"\nRestoring {config.get_program_name(program)} configurations...")
        if not restore_files(source_backup, target_repo, program):
            all_success = False

    if all_success:
        print("\nRestore completed successfully!")
    else:
        print("\nRestore completed with some errors.")

if __name__ == "__main__":
    main()
