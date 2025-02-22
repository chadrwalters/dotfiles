#!/usr/bin/env python3
"""Bootstrap script for setting up new repositories with existing configurations."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import config
from config import get_program_dirs, get_program_files, get_sibling_dirs
from restore import get_available_backups, restore_files, select_backup

config_instance = config.Config()


def check_target_empty(target_repo: Path) -> bool:
    """Check if target repository has any configuration files."""
    has_configs = False

    for program in config_instance.get_all_programs():
        # Check files
        for file in get_program_files(program):
            if (target_repo / file).exists():
                print(f"Found existing config: {file}")
                has_configs = True

        # Check directories
        for dir_name in get_program_dirs(program):
            if (target_repo / dir_name).exists():
                print(f"Found existing config directory: {dir_name}")
                has_configs = True

    return not has_configs


def select_target_repo(repos: List[Path]) -> Optional[Path]:
    """Let user select a repository to set up."""
    if not repos:
        print("No target directories found!")
        return None

    print("\nAvailable directories to set up:")
    for i, repo in enumerate(repos, 1):
        is_git = (repo / ".git").exists()
        print(f"{i}. {repo.name}{' (git)' if is_git else ''}")

    while True:
        try:
            choice = int(input("\nSelect directory to set up [1-{}]: ".format(len(repos))))
            if 1 <= choice <= len(repos):
                return repos[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


def main() -> None:
    """Main function."""
    # Get list of available sibling directories
    print("Looking for directories to set up...")
    dirs = get_sibling_dirs()

    if not dirs:
        print("No sibling directories found to set up!")
        return

    # Let user select which directory to set up
    target_dir = select_target_repo(dirs)

    if not target_dir:
        return

    # Check if target already has configurations
    if not check_target_empty(target_dir):
        print(f"\nWarning: {target_dir.name} already has some configuration files!")
        response = input("Do you want to proceed and potentially overwrite them? [y/N]: ")
        if response.lower() != "y":
            print("Bootstrap cancelled.")
            return

    # Show available backups to use as template
    print("\nSelect which existing configuration to use as template:")
    backups = get_available_backups()

    if not backups:
        print("No configuration backups found! Please backup a working repository first.")
        return

    source_backup = select_backup(backups)

    if not source_backup:
        return

    print(f"\nSetting up {target_dir.name} using configurations from {source_backup.name}")

    # Perform the setup
    all_success = True
    for program in config_instance.get_all_programs():
        print(f"\nSetting up {config_instance.get_program_name(program)} configurations...")
        if not restore_files(source_backup, target_dir, program):
            all_success = False

    if all_success:
        print(
            f"\nSuccessfully set up {target_dir.name} with configurations from {source_backup.name}!"
        )
    else:
        print(
            f"\nSet up completed with some errors. Please check {target_dir.name} configurations."
        )


if __name__ == "__main__":
    main()
