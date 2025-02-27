"""Command line interface for dotfiles."""

from pathlib import Path
from typing import Dict, List, Optional, Set

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .core.backup import BackupManager
from .core.config import Config
from .core.repository import GitRepository
from .core.restore import RestoreManager
from .core.wipe import WipeManager

console = Console()


@click.group()
def cli() -> None:
    """Dotfiles management tool."""


@cli.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    "--programs", "-p", is_flag=True, help="List available programs instead of backing up"
)
@click.option("--branch", "-b", help="Branch to back up")
@click.option("--dry-run", is_flag=True, help="Show what would be backed up without doing it")
def backup(repo_path: Path, programs: bool, branch: Optional[str], dry_run: bool) -> None:
    """Back up program configurations.

    By default, backs up all configured programs. Use --programs to list available programs.
    """
    try:
        if not repo_path.is_dir():
            console.print(f"[red]Error: '{repo_path}' is not a directory")
            raise click.Abort()

        repo = GitRepository(repo_path)
        config = Config()

        # If programs flag is set, just list available programs and exit
        if programs:
            console.print("[bold]Available programs:")
            for program, program_config in config.get_program_configs().items():
                console.print(f"  - {program}: {program_config.get('name', program)}")
            return

        manager = BackupManager(config)

        if not manager.backup(repo, programs=None, branch=branch, dry_run=dry_run):
            console.print("[red]Error: Failed to back up files")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument("repo_name", required=True)
@click.argument("target_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.option("--programs", "-p", multiple=True, help="Programs to restore")
@click.option("--branch", "-b", help="Branch to restore from")
@click.option("--date", "-d", help="Date to restore from (format: YYYYMMDD-HHMMSS)")
@click.option("--latest", "-l", is_flag=True, help="Restore from latest backup")
@click.option("--force", "-f", is_flag=True, help="Force restore even if files exist")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
def restore(
    repo_name: str,
    target_dir: Path,
    programs: Optional[List[str]],
    branch: Optional[str],
    date: Optional[str],
    latest: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Restore program configurations."""
    try:
        config = Config()
        # Create a backup manager to pass to the restore manager
        backup_manager = BackupManager(config)
        manager = RestoreManager(config, backup_manager)

        if not manager.restore(
            repo_name,
            target_dir,
            programs=list(programs) if programs else None,
            branch=branch,
            date=date,
            latest=latest,
            force=force,
            dry_run=dry_run,
        ):
            console.print("[red]Error: Failed to restore files")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument("repo_name", required=True)
@click.option("--branch", "-b", help="Branch to wipe")
@click.option("--date", "-d", help="Date to wipe (format: YYYYMMDD-HHMMSS)")
@click.option("--force", "-f", is_flag=True, help="Force wipe without confirmation")
def wipe(repo_name: str, branch: Optional[str], date: Optional[str], force: bool) -> None:
    """Wipe a backup."""
    try:
        config = Config()
        manager = WipeManager(config)

        # Create a GitRepository object from the repo_name
        # For now, we'll use the current directory as the repo path
        # This is a temporary solution until we update the WipeManager to accept a string repo name
        repo = GitRepository(Path.cwd())

        # The WipeManager.wipe method expects a GitRepository object
        if not manager.wipe(repo, programs=None, force=force):
            console.print("[red]Error: Failed to wipe backup")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


@cli.command()
def init() -> None:
    """Initialize dotfiles configuration."""
    console.print("[bold]Initializing dotfiles configuration...")
    console.print("Not implemented yet.")


@cli.command()
@click.argument("repo", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information about backups")
@click.option(
    "--latest", "-l", is_flag=True, help="Show only the latest backup for each repository"
)
def list(repo: Optional[str], verbose: bool = False, latest: bool = False) -> None:
    """List available backups."""
    config = Config()
    manager = BackupManager(config)
    backups = manager.list_backups(repo)

    if not backups:
        console.print("[yellow]No backups found.")
        return

    # Group backups by repository and branch
    repo_branch_backups: Dict[str, Dict[str, List[Path]]] = {}
    for backup in backups:
        repo_name = backup.parent.parent.name
        branch_name = backup.parent.name

        if repo_name not in repo_branch_backups:
            repo_branch_backups[repo_name] = {}

        if branch_name not in repo_branch_backups[repo_name]:
            repo_branch_backups[repo_name][branch_name] = []

        repo_branch_backups[repo_name][branch_name].append(backup)

    # Sort backups by timestamp (newest first)
    for repo_name in repo_branch_backups:
        for branch_name in repo_branch_backups[repo_name]:
            repo_branch_backups[repo_name][branch_name].sort(key=lambda x: x.name, reverse=True)

    # Create a table for better formatting
    table = Table(title="Available Backups")
    table.add_column("Repository", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Timestamp", style="yellow")
    table.add_column("Programs", style="magenta")

    # Add rows to the table
    for repo_name, branches in repo_branch_backups.items():
        for branch_name, branch_backups in branches.items():
            # If latest flag is set, only show the most recent backup
            backups_to_show = [branch_backups[0]] if latest else branch_backups

            for backup in backups_to_show:
                timestamp = backup.name
                display_timestamp = timestamp

                # Special handling for harmonyhub repository with nested structure
                actual_backup_dir = backup
                if (
                    repo_name == "harmonyhub"
                    and branch_name == "ext"
                    and timestamp == "harmonyhub-clean-pr"
                ):
                    # Look for nested timestamp directory
                    nested_dirs = [d for d in backup.iterdir() if d.is_dir()]
                    if nested_dirs and len(nested_dirs) == 1:
                        actual_backup_dir = nested_dirs[0]
                        # Add a note to the timestamp
                        display_timestamp = f"{timestamp} → {actual_backup_dir.name}"
                elif (
                    repo_name == "harmonyhub"
                    and branch_name == "main"
                    and timestamp == "20250226-184209"
                ):
                    # Look for cursor directory
                    cursor_dir = backup / "cursor"
                    if cursor_dir.exists() and cursor_dir.is_dir():
                        actual_backup_dir = backup

                # Get programs in this backup with file counts
                program_details = []
                program_file_types: Dict[str, Set[str]] = {}

                try:
                    for program_dir in actual_backup_dir.iterdir():
                        if program_dir.is_dir():
                            program_name = program_dir.name

                            # Skip nested timestamp directories in harmonyhub ext branch
                            if (
                                repo_name == "harmonyhub"
                                and branch_name == "ext"
                                and timestamp == "harmonyhub-clean-pr"
                                and program_name == "20250226-184209"
                            ):
                                continue

                            # Count files and directories
                            file_count = 0
                            dir_count = 0
                            file_types = set()

                            for item in program_dir.rglob("*"):
                                if item.is_file():
                                    file_count += 1
                                    # Extract file extension or special file name
                                    if item.name.startswith("."):
                                        file_types.add(item.name)
                                    elif item.suffix:
                                        file_types.add(item.suffix)
                                elif item.is_dir() and item != program_dir:
                                    dir_count += 1

                            program_file_types[program_name] = file_types

                            if verbose:
                                program_details.append(
                                    f"{program_name} ({file_count} files, {dir_count} dirs)"
                                )
                            else:
                                # Show program with file types
                                file_type_str = ", ".join(sorted(file_types)[:3])
                                if len(file_types) > 3:
                                    file_type_str += "..."
                                program_details.append(
                                    f"{program_name}"
                                    + (f" ({file_type_str})" if file_types else "")
                                )
                except (PermissionError, FileNotFoundError):
                    program_details.append("Error reading directory")

                table.add_row(
                    repo_name,
                    branch_name,
                    display_timestamp,
                    ", ".join(program_details) if program_details else "None",
                )

    console.print(table)

    if verbose:
        # Show detailed information for each backup
        for repo_name, branches in repo_branch_backups.items():
            for branch_name, branch_backups in branches.items():
                # If latest flag is set, only show the most recent backup
                backups_to_show = [branch_backups[0]] if latest else branch_backups

                for backup in backups_to_show:
                    timestamp = backup.name
                    display_timestamp = timestamp

                    # Special handling for harmonyhub repository with nested structure
                    actual_backup_dir = backup
                    if (
                        repo_name == "harmonyhub"
                        and branch_name == "ext"
                        and timestamp == "harmonyhub-clean-pr"
                    ):
                        # Look for nested timestamp directory
                        nested_dirs = [d for d in backup.iterdir() if d.is_dir()]
                        if nested_dirs and len(nested_dirs) == 1:
                            actual_backup_dir = nested_dirs[0]
                            # Add a note to the timestamp
                            display_timestamp = f"{timestamp} → {actual_backup_dir.name}"
                    elif (
                        repo_name == "harmonyhub"
                        and branch_name == "main"
                        and timestamp == "20250226-184209"
                    ):
                        # Look for cursor directory
                        cursor_dir = backup / "cursor"
                        if cursor_dir.exists() and cursor_dir.is_dir():
                            actual_backup_dir = backup

                    console.print(f"\n[bold cyan]Repository:[/] {repo_name}")
                    console.print(f"[bold green]Branch:[/] {branch_name}")
                    console.print(f"[bold yellow]Timestamp:[/] {display_timestamp}")
                    console.print(f"[bold yellow]Backup Path:[/] {actual_backup_dir}")

                    # Create a tree for each program
                    try:
                        for program_dir in actual_backup_dir.iterdir():
                            if program_dir.is_dir():
                                # Skip nested timestamp directories in harmonyhub ext branch
                                if (
                                    repo_name == "harmonyhub"
                                    and branch_name == "ext"
                                    and timestamp == "harmonyhub-clean-pr"
                                    and program_dir.name == "20250226-184209"
                                ):
                                    continue

                                program_tree = Tree(f"[bold magenta]{program_dir.name}[/]")

                                # Group files by directory
                                file_groups: Dict[str, List[str]] = {}
                                for item in sorted(program_dir.rglob("*")):
                                    if item.is_file():
                                        parent = item.parent.relative_to(program_dir)
                                        parent_str = str(parent) if parent != Path(".") else ""

                                        if parent_str not in file_groups:
                                            file_groups[parent_str] = []

                                        file_groups[parent_str].append(item.name)

                                # Add files to tree
                                for parent_str, files in sorted(file_groups.items()):
                                    if parent_str:
                                        branch = program_tree.add(f"[bold blue]{parent_str}[/]")
                                        for file in sorted(files):
                                            branch.add(f"[green]{file}[/]")
                                    else:
                                        for file in sorted(files):
                                            program_tree.add(f"[green]{file}[/]")

                                console.print(program_tree)
                    except (PermissionError, FileNotFoundError):
                        console.print("[yellow]Error reading directory[/yellow]")


def main() -> None:
    """Entry point for the dotfiles CLI."""
    cli()


if __name__ == "__main__":
    main()
