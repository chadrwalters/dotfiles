#!/usr/bin/env python3
"""Legacy wipe functionality."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import config
from backup import backup_files, select_repo
from config import BACKUP_DIR, get_program_dirs, get_program_files, get_sibling_repos

config_instance = config.Config()


def get_backup_info(repo_name: str) -> Tuple[bool, Optional[datetime]]:
    """Check if backup exists and get its timestamp."""
    backup_dir = BACKUP_DIR / repo_name

    if not backup_dir.exists():
        return False, None

    # Get the most recent file modification time in the backup
    latest_time = None
    for root, _, files in os.walk(backup_dir):
        for file in files:
            file_path = Path(root) / file
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if latest_time is None or mtime > latest_time:
                latest_time = mtime

    return True, latest_time


def wipe_configs(target_repo: Path) -> bool:
    """Remove all configuration files from the repository."""
    success = True

    for program in config_instance.get_all_programs():
        # Remove files
        for file in get_program_files(program):
            file_path = target_repo / file
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Removed: {file}")
                except Exception as e:
                    print(f"Error removing {file}: {e}")
                    success = False

        # Remove directories
        for dir_name in get_program_dirs(program):
            dir_path = target_repo / dir_name
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    print(f"Removed directory: {dir_name}")
                except Exception as e:
                    print(f"Error removing directory {dir_name}: {e}")
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
    target_repo = select_repo(repos)
    if not target_repo:
        return

    # Check for existing backup
    has_backup, backup_time = get_backup_info(target_repo.name)
    if not has_backup:
        print("\nNo existing backup found.")
        response = input("Would you like to create a backup before wiping? [Y/n]: ")
        if response.lower() != "n":
            print("\nCreating backup...")
            all_success = True
            for program in config_instance.get_all_programs():
                print(f"\nBacking up {config_instance.get_program_name(program)} configurations...")
                if not backup_files(target_repo, program):
                    all_success = False

            if all_success:
                print("\nBackup completed successfully.")
            else:
                print("Backup completed with some errors.")
                response = input("\nDo you want to proceed with wipe anyway? [y/N]: ")
                if response.lower() != "y":
                    print("Wipe cancelled.")
                    return
        else:
            response = input("\nAre you sure you want to proceed without backup? [y/N]: ")
            if response.lower() != "y":
                print("Wipe cancelled.")
                return
    else:
        print(f"\nFound backup from: {backup_time}")

    print(f"\nWarning: This will remove all configuration files from {target_repo.name}")
    response = input("Are you sure you want to proceed? [y/N]: ")
    if response.lower() != "y":
        print("Wipe cancelled.")
        return

    # Wipe configurations
    success = wipe_configs(target_repo)
    if success:
        print("\nWipe completed successfully.")
    else:
        print("\nWipe completed with some errors.")


if __name__ == "__main__":
    main()
