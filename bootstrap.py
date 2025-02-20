#!/usr/bin/env python3
"""Bootstrap script for setting up new repositories with existing configurations."""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import config
from backup import get_sibling_repos, select_repo
from restore import get_available_backups, select_backup, check_conflicts, restore_files

def check_target_empty(target_repo: Path) -> bool:
    """Check if target repository has any configuration files."""
    has_configs = False

    for program in config.get_all_programs():
        # Check files
        for file in config.get_program_files(program):
            if (target_repo / file).exists():
                print(f"Found existing config: {file}")
                has_configs = True

        # Check directories
        for dir_name in config.get_program_dirs(program):
            if (target_repo / dir_name).exists():
                print(f"Found existing config directory: {dir_name}")
                has_configs = True

    return not has_configs

def main():
    """Main function."""
    # Get target repository to bootstrap
    print("Select repository to bootstrap:")
    repos = get_sibling_repos()
    target_repo = select_repo(repos)

    if not target_repo:
        return

    # Check if target has any configurations
    if not check_target_empty(target_repo):
        print("\nWarning: Target repository already has some configuration files!")
        response = input("Do you want to proceed anyway? [y/N]: ")
        if response.lower() != 'y':
            print("Bootstrap cancelled.")
            return

    # Get source backup to use as template
    print("\nSelect source backup to bootstrap from:")
    backups = get_available_backups()
    source_backup = select_backup(backups)

    if not source_backup:
        return

    print(f"\nBootstrapping {target_repo.name} with configurations from {source_backup.name}")

    # Perform the restore
    all_success = True
    for program in config.get_all_programs():
        print(f"\nSetting up {config.get_program_name(program)} configurations...")
        if not restore_files(source_backup, target_repo, program):
            all_success = False

    if all_success:
        print("\nBootstrap completed successfully!")
    else:
        print("\nBootstrap completed with some errors.")

if __name__ == "__main__":
    main()
