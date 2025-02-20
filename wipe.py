#!/usr/bin/env python3
"""Wipe script for removing configurations from repositories."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import config
from backup import get_sibling_repos, select_repo, backup_files

def get_backup_info(repo_name: str) -> Tuple[bool, Optional[datetime]]:
    """Check if backup exists and get its timestamp."""
    backup_dir = config.BACKUP_DIR / repo_name

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

    for program in config.get_all_programs():
        # Remove files
        for file in config.get_program_files(program):
            file_path = target_repo / file
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Removed: {file}")
                except Exception as e:
                    print(f"Error removing {file}: {e}")
                    success = False

        # Remove directories
        for dir_name in config.get_program_dirs(program):
            dir_path = target_repo / dir_name
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    print(f"Removed directory: {dir_name}")
                except Exception as e:
                    print(f"Error removing directory {dir_name}: {e}")
                    success = False

    return success

def main():
    """Main function."""
    # Get repository to wipe
    print("Select repository to wipe configurations from:")
    repos = get_sibling_repos()
    target_repo = select_repo(repos)

    if not target_repo:
        return

    # Check for existing backup
    has_backup, backup_time = get_backup_info(target_repo.name)

    if has_backup:
        print(f"\nFound existing backup from: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\nNo existing backup found.")
        response = input("Would you like to create a backup before wiping? [Y/n]: ")
        if response.lower() != 'n':
            print("\nCreating backup...")
            all_success = True
            for program in config.get_all_programs():
                print(f"\nBacking up {config.get_program_name(program)} configurations...")
                if not backup_files(target_repo, program):
                    all_success = False

            if all_success:
                print("Backup completed successfully!")
            else:
                print("Backup completed with some errors.")
                response = input("\nDo you want to proceed with wipe anyway? [y/N]: ")
                if response.lower() != 'y':
                    print("Wipe cancelled.")
                    return

    # Confirm wipe
    print(f"\nWarning: This will remove all configuration files from {target_repo.name}")
    response = input("Are you sure you want to proceed? [y/N]: ")
    if response.lower() != 'y':
        print("Wipe cancelled.")
        return

    # Perform the wipe
    if wipe_configs(target_repo):
        print("\nWipe completed successfully!")
    else:
        print("\nWipe completed with some errors.")

if __name__ == "__main__":
    main()
