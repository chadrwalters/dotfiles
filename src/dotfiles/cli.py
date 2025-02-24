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


def validate_programs(ctx, param, value):
    """Validate and convert programs to a list."""
    if not value:
        return None
    return list(value)


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
@click.argument(
    "backup_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.argument("target_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.option("--force", is_flag=True, help="Force restore over existing files")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
def restore(backup_dir: Path, target_dir: Path, force: bool = False, dry_run: bool = False):
    """Restore files from backup to target directory."""
    config = Config()
    backup_manager = BackupManager(config)
    manager = RestoreManager(config, backup_manager)

    if not backup_dir.exists():
        console.print(f"[red]Error: Backup directory {backup_dir} does not exist")
        raise click.Abort()

    if not backup_dir.is_dir():
        console.print(f"[red]Error: {backup_dir} is not a directory")
        raise click.Abort()

    try:
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Git repository if it doesn't exist
        repo = GitRepository(target_dir)

        # Get list of programs to restore (only those that exist in the backup directory)
        available_programs = []
        for program in config.programs.keys():
            program_dir = backup_dir / program
            if program_dir.exists() and program_dir.is_dir():
                available_programs.append(program)

        if not available_programs:
            console.print("[yellow]No program directories found in the backup[/yellow]")
            return

        console.print(
            f"Found {len(available_programs)} program(s) to restore: {', '.join(available_programs)}"
        )

        # Restore each program
        any_restored = False
        for program in available_programs:
            with console.status(f"Restoring {program} configurations..."):
                if manager.restore_program(program, backup_dir, target_dir, force, dry_run):
                    any_restored = True

        if not any_restored:
            console.print("[yellow]No files were restored[/yellow]")
            return

        if not dry_run:
            console.print(f"Restored files to {target_dir}")

            # Validate the restore
            console.print("\nValidating restore...")
            is_valid, validation_results = manager.validate_restore(
                backup_dir, target_dir, available_programs
            )
            manager.display_validation_results(validation_results)

            if not is_valid:
                console.print(
                    "[yellow]Warning: Some files may not have been restored correctly[/yellow]"
                )
            else:
                console.print("[green]All files restored successfully![/green]")
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
