#!/usr/bin/env python3
"""Backup script for dotfiles."""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import config

def get_sibling_repos() -> List[Path]:
    """Get list of sibling repositories."""
    current_dir = Path.cwd()
    parent_dir = current_dir.parent
    return [d for d in parent_dir.iterdir()
            if d.is_dir() and d != current_dir and (d / '.git').exists()]

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
    backup_dir = config.BACKUP_DIR / source_repo.name / program
    backup_dir.mkdir(parents=True, exist_ok=True)

    success = True

    # Backup individual files
    for file in config.get_program_files(program):
        source_file = source_repo / file
        if source_file.exists():
            try:
                shutil.copy2(source_file, backup_dir / file)
                print(f"Backed up: {file}")
            except Exception as e:
                print(f"Error backing up {file}: {e}")
                success = False

    # Backup directories
    for dir_name in config.get_program_dirs(program):
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

def main():
    """Main function."""
    repos = get_sibling_repos()
    source_repo = select_repo(repos)

    if not source_repo:
        return

    print(f"\nBacking up from: {source_repo.name}")

    all_success = True
    for program in config.get_all_programs():
        print(f"\nBacking up {config.get_program_name(program)} configurations...")
        if not backup_files(source_repo, program):
            all_success = False

    if all_success:
        print("\nBackup completed successfully!")
    else:
        print("\nBackup completed with some errors.")

if __name__ == "__main__":
    main()
