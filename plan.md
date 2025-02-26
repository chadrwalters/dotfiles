# Implementation Plan: Improving Dotfiles Restore Command

## Overview

This plan outlines the steps to enhance the `restore` command in the dotfiles CLI tool to make it more user-friendly. The primary goals are:

1. Allow users to specify a repository name instead of full paths
2. Support backup date selection with a simple format
3. Add a `--latest` flag to explicitly select the latest backup
4. Improve error handling and user feedback

## Current Issues

- The restore command requires full paths which is cumbersome
- Users need to know the exact backup directory structure
- No easy way to select backups by date
- Command syntax is not intuitive for new users

## Proposed Solution

### New Command Interface

```bash
dotfiles restore [REPO_NAME] [TARGET_DIR] [--date DATE] [--latest] [--force] [--dry-run] [--program PROGRAM]
```

Where:
- `REPO_NAME`: Optional repository name to restore from (defaults to target directory name)
- `TARGET_DIR`: Optional target directory (defaults to current directory)
- `--date`: Optional date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS)
- `--latest`: Flag to use the latest backup (this is already the default behavior, but makes it explicit)
- `--force`: Force restore over existing files
- `--dry-run`: Show what would be restored without doing it
- `--program`: Program to restore (can be specified multiple times)

### Implementation Steps

## Step 1: Update the RestoreManager class

Enhance the `find_backup` method in `RestoreManager` to support finding a backup by date.

File: `src/dotfiles/core/restore.py`

```python
def find_backup(
    self,
    repo_name: str,
    date: Optional[str] = None,
    branch: Optional[str] = None,
    latest: bool = False
) -> Optional[Path]:
    """Find a backup for a repository.

    Args:
        repo_name: Name of the repository to find backups for.
        date: Optional date string in format YYYYMMDD or YYYYMMDD-HHMMSS to find a specific backup.
        branch: Optional branch name to filter backups by.
        latest: If True, return the latest backup regardless of date parameter.

    Returns:
        Path to the backup directory if found, None otherwise.
    """
    # Ensure we're using an absolute path for the backup directory
    backup_dir = self.backup_dir
    if not backup_dir.is_absolute():
        # If we're in the dotfiles repository, use the relative path
        if Path.cwd().name == "dotfiles":
            backup_dir = Path.cwd() / backup_dir
        else:
            # Try to find the dotfiles repository
            dotfiles_path = Path.home() / "source" / "dotfiles"
            if dotfiles_path.exists():
                backup_dir = dotfiles_path / backup_dir
            else:
                # Fall back to the current directory
                backup_dir = Path.cwd() / backup_dir

    if not backup_dir.exists():
        self.console.print(f"[yellow]Backup directory {backup_dir} does not exist[/yellow]")
        return None

    repo_dir = backup_dir / repo_name
    if not repo_dir.exists():
        self.console.print(f"[yellow]No backups found for repository '{repo_name}'[/yellow]")
        return None

    # If branch specified, look in that branch directory
    if branch:
        branch_dir = repo_dir / branch
        if not branch_dir.exists():
            self.console.print(f"[yellow]No backups found for branch '{branch}' in repository '{repo_name}'[/yellow]")
            return None
        backups = list(branch_dir.iterdir())
    else:
        # Otherwise look in all branch directories
        backups = []
        for branch_dir in repo_dir.iterdir():
            if branch_dir.is_dir():
                backups.extend(branch_dir.iterdir())

    if not backups:
        self.console.print(f"[yellow]No backups found for repository '{repo_name}'[/yellow]")
        return None

    # If latest flag is set, ignore date and return latest backup
    if latest:
        return max(backups, key=lambda p: datetime.strptime(p.name, "%Y%m%d-%H%M%S"))

    # If date is specified, filter backups by date
    if date:
        # Handle both full timestamp and date-only formats
        matching_backups = []
        for backup in backups:
            if date == backup.name:  # Exact match for full timestamp (YYYYMMDD-HHMMSS)
                return backup
            elif len(date) == 8 and backup.name.startswith(date):  # Date-only match (YYYYMMDD)
                matching_backups.append(backup)

        if matching_backups:
            # Return latest backup for that date
            return max(matching_backups, key=lambda p: p.name)
        else:
            self.console.print(f"[yellow]No backups found for date '{date}' in repository '{repo_name}'[/yellow]")
            return None

    # Otherwise return latest backup
    return max(backups, key=lambda p: datetime.strptime(p.name, "%Y%m%d-%H%M%S"))
```

## Step 2: Update the restore method in RestoreManager

Update the `restore` method to handle the repository name instead of requiring a GitRepository object.

File: `src/dotfiles/core/restore.py`

```python
def restore(
    self,
    repo_or_name: Union[GitRepository, str, Path],
    target_dir: Optional[Path] = None,
    programs: Optional[List[str]] = None,
    branch: Optional[str] = None,
    date: Optional[str] = None,
    latest: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Restore program configurations.

    Args:
        repo_or_name: Git repository to restore to, repository name, or path to target directory.
        target_dir: Optional target directory to restore to.
        programs: Optional list of programs to restore.
        branch: Optional branch to restore from.
        date: Optional date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS).
        latest: Whether to use the latest backup regardless of date.
        force: Whether to force restore over existing files.
        dry_run: Whether to perform a dry run.

    Returns:
        True if restore was successful, False otherwise.
    """
    # Convert repo_or_name to GitRepository and target_dir
    if isinstance(repo_or_name, str):
        # It's a repository name, we need to determine the target directory
        # and then create a GitRepository
        repo_name = repo_or_name
        if target_dir is None:
            # Default to current directory if no target dir specified
            target_dir = Path.cwd()
            self.console.print(f"[yellow]No target directory specified, using current directory: {target_dir}[/yellow]")
        repo = GitRepository(target_dir)
    elif isinstance(repo_or_name, Path):
        # It's a path, create a GitRepository from it
        target_dir = repo_or_name
        repo = GitRepository(target_dir)
    else:
        # It's already a GitRepository
        repo = repo_or_name
        if target_dir is None:
            target_dir = repo.path

    # Make sure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Find backup
    if isinstance(repo_or_name, str):
        # We were given a repo name directly
        backup_path = self.find_backup(repo_name, date, branch, latest)
    else:
        # We need to extract repo name from the GitRepository
        backup_path = self.find_backup(repo.name, date, branch, latest)

    if backup_path is None:
        return False

    # Check for conflicts
    if not force and not dry_run:
        conflicts = self.check_conflicts(repo, backup_path)
        if conflicts:
            self.console.print("[yellow]Conflicts found:[/yellow]")
            for target_path, backup_file in conflicts:
                self.console.print(f"  {target_path.relative_to(repo.path)} (exists in target and backup)")
            self.console.print("[yellow]Use --force to overwrite existing files[/yellow]")
            return False

    # Get list of programs to restore
    if not programs:
        programs = []
        for program_dir in backup_path.iterdir():
            if program_dir.is_dir() and program_dir.name in self.config.programs:
                programs.append(program_dir.name)
    else:
        # Validate programs
        invalid_programs = [p for p in programs if p not in self.config.programs]
        if invalid_programs:
            self.console.print(f"[yellow]Invalid programs: {', '.join(invalid_programs)}[/yellow]")
            return False

    if not programs:
        self.console.print("[yellow]No programs to restore[/yellow]")
        return False

    # Restore each program
    any_restored = False
    for program in programs:
        with self.console.status(f"Restoring {program} configurations..."):
            if self.restore_program(program, backup_path, target_dir, force, dry_run):
                any_restored = True

    if not any_restored:
        self.console.print("[yellow]No files were restored[/yellow]")
        return False

    if not dry_run:
        self.console.print(f"[green]Restored files to {target_dir}[/green]")

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

    return True
```

## Step 3: Update the CLI restore command

Update the CLI command in `src/dotfiles/cli.py` to support the new parameters:

```python
@cli.command()
@click.argument("repo_name", required=False)
@click.argument("target_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), required=False)
@click.option("--date", "-d", help="Date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS)")
@click.option("--branch", "-b", help="Branch to restore from")
@click.option("--latest", "-l", is_flag=True, help="Use the latest backup")
@click.option("--force", "-f", is_flag=True, help="Force restore over existing files")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
@click.option(
    "--program", "-p",
    multiple=True,
    callback=validate_programs,
    help="Program to restore (can be specified multiple times)"
)
def restore(
    repo_name: Optional[str] = None,
    target_dir: Optional[Path] = None,
    date: Optional[str] = None,
    branch: Optional[str] = None,
    latest: bool = False,
    force: bool = False,
    dry_run: bool = False,
    program: Optional[List[str]] = None,
):
    """Restore files from backup.

    REPO_NAME is the name of the repository to restore from. If not specified,
    will try to determine it from the target directory name or current directory.

    TARGET_DIR is the directory to restore configurations to. If not specified,
    will use the current directory.

    Examples:
      # Restore latest backup for the current directory
      dotfiles restore

      # Restore from a specific repository to current directory
      dotfiles restore cursor-tools

      # Restore from a specific repository to a different directory
      dotfiles restore cursor-tools ~/source/consolidate-markdown/

      # Restore from a specific date (can use YYYYMMDD or YYYYMMDD-HHMMSS format)
      dotfiles restore cursor-tools --date 20250226

      # Restore latest backup regardless of date
      dotfiles restore cursor-tools --latest

      # Restore specific programs only
      dotfiles restore cursor-tools --program cursor --program git
    """
    config = Config()
    backup_manager = BackupManager(config)
    manager = RestoreManager(config, backup_manager)

    try:
        # Determine target directory if not specified
        if target_dir is None:
            target_dir = Path.cwd()
            console.print(f"[yellow]No target directory specified, using current directory: {target_dir}[/yellow]")

        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # If repo_name is not specified, try to determine it
        if repo_name is None:
            # Try to use target directory name
            repo_name = target_dir.name
            console.print(f"[yellow]No repository name specified, using target directory name: {repo_name}[/yellow]")

        # Check if the repository name exists in the backups directory
        if repo_name:
            backups = backup_manager.list_backups(repo_name)
            if not backups:
                console.print(f"[yellow]No backups found for repository '{repo_name}'[/yellow]")
                # List available repositories
                all_backups = backup_manager.list_backups()
                if all_backups:
                    repo_names = sorted(set(backup.parent.parent.name for backup in all_backups))
                    console.print("[yellow]Available repositories:[/yellow]")
                    for name in repo_names:
                        console.print(f"  - {name}")
                raise click.Abort()

        # Restore configurations
        if not manager.restore(
            repo_name,
            target_dir,
            programs=program,
            branch=branch,
            date=date,
            latest=latest,
            force=force,
            dry_run=dry_run
        ):
            console.print("[red]Error: Failed to restore files[/red]")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
```

## Step 4: Update imports and typing

Add necessary imports to both files:

File: `src/dotfiles/core/restore.py`:
```python
from __future__ import annotations
import filecmp
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from rich.console import Console
from rich.table import Table
from .backup import BackupManager
from .config import Config
from .repository import GitRepository
```

## Step 5: Update README.md

Update the README.md file to reflect the new command structure:

```markdown
### Restore Operations

```bash
# Restore to a target directory using the latest backup (automatically detected)
dotfiles restore cursor-tools

# Restore from a specific backup date
dotfiles restore cursor-tools --date 20250226

# Restore to a specific directory
dotfiles restore cursor-tools ~/source/consolidate-markdown/

# Force restore over existing files
dotfiles restore cursor-tools --force

# Perform a dry run (show what would be restored without doing it)
dotfiles restore cursor-tools --dry-run

# Restore specific programs only
dotfiles restore cursor-tools --program cursor --program git
```
```

## Step 6: Update Test Cases

To ensure our new functionality works correctly, we need to update the existing test cases and add new ones to cover the enhanced features. The test updates should be made in the `tests/test_restore.py` file.

### 1. Update Test Fixtures

```python
@pytest.fixture
def mock_backup_structure(tmp_path):
    """Create a mock backup structure with multiple repositories, branches, and dates."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # Create repo1 with main branch and two backup dates
    repo1_dir = backup_dir / "repo1" / "main"
    repo1_dir.mkdir(parents=True)

    # Create two backups for repo1
    backup1 = repo1_dir / "20250101-120000"
    backup1.mkdir()
    (backup1 / "git").mkdir()
    (backup1 / "git" / ".gitconfig").write_text("content1")

    backup2 = repo1_dir / "20250102-120000"  # newer backup
    backup2.mkdir()
    (backup2 / "git").mkdir()
    (backup2 / "git" / ".gitconfig").write_text("content2")

    # Create repo2 with main branch and one backup date
    repo2_dir = backup_dir / "repo2" / "main"
    repo2_dir.mkdir(parents=True)

    backup3 = repo2_dir / "20250103-120000"
    backup3.mkdir()
    (backup3 / "vscode").mkdir()
    (backup3 / "vscode" / "settings.json").write_text("vscode settings")

    # Create repo3 with multiple branches
    repo3_main_dir = backup_dir / "repo3" / "main"
    repo3_main_dir.mkdir(parents=True)

    backup4 = repo3_main_dir / "20250104-120000"
    backup4.mkdir()
    (backup4 / "cursor").mkdir()
    (backup4 / "cursor" / "settings.json").write_text("cursor settings main")

    repo3_dev_dir = backup_dir / "repo3" / "dev"
    repo3_dev_dir.mkdir(parents=True)

    backup5 = repo3_dev_dir / "20250104-130000"
    backup5.mkdir()
    (backup5 / "cursor").mkdir()
    (backup5 / "cursor" / "settings.json").write_text("cursor settings dev")

    # Create repo with multiple backups on the same day
    repo4_dir = backup_dir / "repo4" / "main"
    repo4_dir.mkdir(parents=True)

    backup6 = repo4_dir / "20250105-090000"
    backup6.mkdir()
    (backup6 / "git").mkdir()
    (backup6 / "git" / ".gitconfig").write_text("morning config")

    backup7 = repo4_dir / "20250105-180000"  # same day, later time
    backup7.mkdir()
    (backup7 / "git").mkdir()
    (backup7 / "git" / ".gitconfig").write_text("evening config")

    return backup_dir
```

### 2. Test Finding Backups by Repository Name

```python
def test_find_backup_by_repo_name(mock_backup_structure, monkeypatch):
    """Test finding a backup by repository name."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Test finding the latest backup for repo1
    backup_path = restore_manager.find_backup("repo1")
    assert backup_path is not None
    assert backup_path.name == "20250102-120000"  # Should find the newest backup

    # Test finding the latest backup for repo2
    backup_path = restore_manager.find_backup("repo2")
    assert backup_path is not None
    assert backup_path.name == "20250103-120000"

    # Test finding a backup for a non-existent repo
    backup_path = restore_manager.find_backup("non_existent_repo")
    assert backup_path is None
```

### 3. Test Finding Backups by Date

```python
def test_find_backup_by_date(mock_backup_structure, monkeypatch):
    """Test finding a backup by date."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Test finding a backup by exact timestamp
    backup_path = restore_manager.find_backup("repo1", date="20250101-120000")
    assert backup_path is not None
    assert backup_path.name == "20250101-120000"

    # Test finding a backup by date only (should return latest for that date)
    backup_path = restore_manager.find_backup("repo4", date="20250105")
    assert backup_path is not None
    assert backup_path.name == "20250105-180000"  # Should find the latest backup for that date

    # Test finding a backup for a non-existent date
    backup_path = restore_manager.find_backup("repo1", date="20250110")
    assert backup_path is None
```

### 4. Test Finding Backups with Latest Flag

```python
def test_find_backup_with_latest_flag(mock_backup_structure, monkeypatch):
    """Test finding a backup with the latest flag."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Test finding the latest backup with the latest flag
    backup_path = restore_manager.find_backup("repo1", latest=True)
    assert backup_path is not None
    assert backup_path.name == "20250102-120000"

    # Test that latest flag overrides date parameter
    backup_path = restore_manager.find_backup("repo1", date="20250101-120000", latest=True)
    assert backup_path is not None
    assert backup_path.name == "20250102-120000"  # Should still find the latest backup
```

### 5. Test Finding Backups by Branch

```python
def test_find_backup_by_branch(mock_backup_structure, monkeypatch):
    """Test finding a backup by branch."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Test finding a backup for a specific branch
    backup_path = restore_manager.find_backup("repo3", branch="main")
    assert backup_path is not None
    assert backup_path.name == "20250104-120000"

    backup_path = restore_manager.find_backup("repo3", branch="dev")
    assert backup_path is not None
    assert backup_path.name == "20250104-130000"

    # Test finding a backup for a non-existent branch
    backup_path = restore_manager.find_backup("repo3", branch="non_existent_branch")
    assert backup_path is None
```

### 6. Test Restore with Repository Name

```python
def test_restore_with_repo_name(mock_backup_structure, tmp_path, monkeypatch):
    """Test restoring with a repository name."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Test restoring with a repository name
    result = restore_manager.restore("repo1", target_dir)
    assert result is True

    # Check that the files were restored
    restored_file = target_dir / ".gitconfig"
    assert restored_file.exists()
    assert restored_file.read_text() == "content2"  # Should restore from the latest backup
```

### 7. Test Restore with Date Parameter

```python
def test_restore_with_date(mock_backup_structure, tmp_path, monkeypatch):
    """Test restoring with a date parameter."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Test restoring with a specific date
    result = restore_manager.restore("repo1", target_dir, date="20250101-120000")
    assert result is True

    # Check that the files were restored from the correct backup
    restored_file = target_dir / ".gitconfig"
    assert restored_file.exists()
    assert restored_file.read_text() == "content1"  # Should restore from the specified backup
```

### 8. Test Restore with Latest Flag

```python
def test_restore_with_latest_flag(mock_backup_structure, tmp_path, monkeypatch):
    """Test restoring with the latest flag."""
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    # Mock the backup_dir property
    monkeypatch.setattr(restore_manager, "backup_dir", mock_backup_structure)

    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Test restoring with the latest flag
    result = restore_manager.restore("repo1", target_dir, latest=True)
    assert result is True

    # Check that the files were restored from the latest backup
    restored_file = target_dir / ".gitconfig"
    assert restored_file.exists()
    assert restored_file.read_text() == "content2"  # Should restore from the latest backup
```

### 9. Test CLI Command

```python
def test_cli_restore_command(mock_backup_structure, tmp_path, monkeypatch, runner):
    """Test the CLI restore command."""
    # Mock the backup directory
    monkeypatch.setattr(BackupManager, "backup_dir", mock_backup_structure)

    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Test the CLI command with a repository name
    result = runner.invoke(cli, ["restore", "repo1", str(target_dir)])
    assert result.exit_code == 0

    # Check that the files were restored
    restored_file = target_dir / ".gitconfig"
    assert restored_file.exists()
    assert restored_file.read_text() == "content2"  # Should restore from the latest backup

    # Test the CLI command with a date parameter
    target_dir2 = tmp_path / "target2"
    target_dir2.mkdir()

    result = runner.invoke(cli, ["restore", "repo1", str(target_dir2), "--date", "20250101-120000"])
    assert result.exit_code == 0

    # Check that the files were restored from the correct backup
    restored_file = target_dir2 / ".gitconfig"
    assert restored_file.exists()
    assert restored_file.read_text() == "content1"  # Should restore from the specified backup
```

## Testing Plan

1. Basic functionality testing:
   - Test restoring with just a repository name
   - Test restoring with repository name and target directory
   - Test restoring with repository name and date
   - Test restoring with repository name and the `--latest` flag

2. Edge case testing:
   - Test with non-existent repository name
   - Test with invalid date format
   - Test with date that doesn't have any backups
   - Test with empty backup directory

## Expected Benefits

1. **Simplified Command Usage**: Users can now specify just a repository name instead of full paths
2. **Intuitive Date Selection**: Easy selection of backups by date
3. **Better Defaults**: Sensible defaults that work in most cases
4. **Improved Error Handling**: Better error messages and suggestions
5. **Enhanced Documentation**: Clear examples for common use cases

## Timeline

1. Day 1: Implement changes to `find_backup` method and update imports
2. Day 2: Implement changes to `restore` method
3. Day 3: Update CLI command and add documentation
4. Day 4: Testing and bug fixes
5. Day 5: Documentation updates and final review
