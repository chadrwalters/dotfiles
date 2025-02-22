#!/usr/bin/env python3
"""Legacy backup functionality."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

import config
from config import BACKUP_DIR, get_program_dirs, get_program_files, get_sibling_repos

config_instance = config.Config()


def select_repo(repos: List[Path]) -> Optional[Path]:
    """Let user select a repository to backup from."""
    if not repos:
        print("No sibling repositories found!")
        return None

    print("\nAvailable repositories:")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo.name}")

    while True:
        try:
            choice = int(input("\nSelect repo to backup [1-{}]: ".format(len(repos))))
            if 1 <= choice <= len(repos):
                return repos[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


def backup_files(source_repo: Path, program: str) -> bool:
    """Backup files for a specific program."""
    backup_dir = BACKUP_DIR / source_repo.name / program
    backup_dir.mkdir(parents=True, exist_ok=True)

    success = True

    # Backup individual files
    for file in get_program_files(program):
        source_file = source_repo / file
        if source_file.exists():
            try:
                shutil.copy2(source_file, backup_dir / file)
                print(f"Backed up: {file}")
            except Exception as e:
                print(f"Error backing up {file}: {e}")
                success = False

    # Backup directories
    for dir_name in get_program_dirs(program):
        source_dir = source_repo / dir_name
        if source_dir.exists():
            target_dir = backup_dir / dir_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            try:
                shutil.copytree(source_dir, target_dir)
                print(f"Backed up directory: {dir_name}")
            except Exception as e:
                print(f"Error backing up directory {dir_name}: {e}")
                success = False

    return success


def main() -> None:
    """Main function."""
    # Get available repositories
    repos = get_sibling_repos()
    if not repos:
        print("No Git repositories found.")
        return

    # Let user select repository
    source_repo = select_repo(repos)
    if not source_repo:
        return

    # Get program to backup
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

    # Backup files
    success = backup_files(source_repo, program)
    if success:
        print("\nBackup completed successfully.")
    else:
        print("\nBackup completed with some errors.")


if __name__ == "__main__":
    main()
