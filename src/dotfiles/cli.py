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
def cli():
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
def backup(repo_path: Path, programs: bool, branch: Optional[str], dry_run: bool):
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
@click.argument("repo_name", required=False)
@click.argument(
    "target_dir", required=False, type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.option("--date", "-d", help="Date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS)")
@click.option("--branch", "-b", help="Branch to restore from")
@click.option("--latest", "-l", is_flag=True, help="Use the latest backup")
@click.option("--force", "-f", is_flag=True, help="Force restore over existing files")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
def restore(
    repo_name: Optional[str] = None,
    target_dir: Optional[Path] = None,
    date: Optional[str] = None,
    branch: Optional[str] = None,
    latest: bool = False,
    force: bool = False,
    dry_run: bool = False,
):
    """Restore files from backup.

    REPO_NAME is the name of the repository to restore from. If not specified,
    will try to determine it from the target directory or current directory.

    TARGET_DIR is the directory to restore configurations to. If not specified,
    will use the current directory.

    Examples:
      # Restore latest backup for the current directory
      dotfiles restore

      # Restore from a specific repository to current directory
      dotfiles restore cursor-tools

      # Restore from a specific repository to a different directory
      dotfiles restore cursor-tools /tmp/test-restore

      # Restore from "main" branch
      dotfiles restore cursor-tools --branch main

      # Restore from a specific date (can use YYYYMMDD or YYYYMMDD-HHMMSS format)
      dotfiles restore cursor-tools --date 20250226

      # Restore latest backup, ignoring date and branch parameters if any
      dotfiles restore cursor-tools --latest
    """
    config = Config()
    backup_manager = BackupManager(config)
    restore_manager = RestoreManager(config, backup_manager)

    try:
        # Determine target directory if not specified
        if target_dir is None:
            target_dir = Path.cwd()
            console.print(
                f"[yellow]No target directory specified, using current directory: {target_dir}[/yellow]"
            )

        # Determine repo name if not specified
        if repo_name is None:
            repo_name = target_dir.name  # Use target directory name as default
            console.print(f"[yellow]No repository name specified, assuming: {repo_name}[/yellow]")

        if not restore_manager.restore(
            repo_name=repo_name,
            target_dir=target_dir,
            programs=None,
            branch=branch,
            date=date,
            latest=latest,
            force=force,
            dry_run=dry_run,
        ):
            console.print("[red]Error: Failed to restore files[/red]")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument("repo", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information about backups")
@click.option(
    "--latest", "-l", is_flag=True, help="Show only the latest backup for each repository"
)
def list(repo: Optional[str], verbose: bool = False, latest: bool = False):
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

                # Get programs in this backup with file counts
                program_details = []
                program_file_types: Dict[str, Set[str]] = {}

                for program_dir in backup.iterdir():
                    if program_dir.is_dir():
                        program_name = program_dir.name

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
                                f"{program_name}" + (f" ({file_type_str})" if file_types else "")
                            )

                table.add_row(
                    repo_name,
                    branch_name,
                    timestamp,
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

                    console.print(f"\n[bold cyan]Repository:[/] {repo_name}")
                    console.print(f"[bold green]Branch:[/] {branch_name}")
                    console.print(f"[bold yellow]Timestamp:[/] {timestamp}")

                    # Create a tree for each program
                    for program_dir in backup.iterdir():
                        if program_dir.is_dir():
                            program_tree = Tree(f"[bold magenta]{program_dir.name}[/]")

                            # Group files by directory
                            file_groups = {}
                            for item in sorted(program_dir.rglob("*")):
                                if item.is_file():
                                    parent = item.parent.relative_to(program_dir)
                                    parent_str = str(parent) if parent != Path(".") else ""

                                    if parent_str not in file_groups:
                                        file_groups[parent_str] = []

                                    file_groups[parent_str].append(item.name)

                            # Add files to tree
                            for parent, files in sorted(file_groups.items()):
                                if parent:
                                    branch = program_tree.add(f"[bold blue]{parent}[/]")
                                    for file in sorted(files):
                                        branch.add(f"[green]{file}[/]")
                                else:
                                    for file in sorted(files):
                                        program_tree.add(f"[green]{file}[/]")

                            console.print(program_tree)


@cli.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option("--programs", "-p", is_flag=True, help="List available programs instead of wiping")
@click.option("--force", "-f", is_flag=True, help="Force wipe without confirmation")
@click.option("--dry-run", is_flag=True, help="Show what would be wiped without doing it")
def wipe(repo_path: Path, programs: bool, force: bool, dry_run: bool):
    """Wipe program configurations.

    By default, wipes all configured programs. Use --programs to list available programs.
    """
    try:
        repo = GitRepository(repo_path)
        config = Config()

        # If programs flag is set, just list available programs and exit
        if programs:
            console.print("[bold]Available programs:")
            for program, program_config in config.get_program_configs().items():
                console.print(f"  - {program}: {program_config.get('name', program)}")
            return

        manager = WipeManager(config)

        if not manager.wipe(repo, programs=None, force=force, dry_run=dry_run):
            console.print("[red]Error: Failed to wipe files")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


def main():
    """Entry point for the dotfiles CLI."""
    cli()


if __name__ == "__main__":
    main()
