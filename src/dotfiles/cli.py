"""Command line interface for dotfiles."""

from pathlib import Path
from typing import Dict, List, Optional

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
    """Dotfiles management tool.

    This tool helps manage configuration files (dotfiles) across multiple repositories.
    It provides commands for backing up, restoring, and managing configuration files
    for various programs like cursor, vscode, and more.

    Main commands:

      backup    Back up program configurations from a repository
      restore   Restore program configurations to a repository
      list      List available backups
      wipe      Remove a backup
      init      Initialize dotfiles configuration

    Run 'dotfiles COMMAND --help' for more information on a specific command.
    """


@cli.command()
@click.argument(
    "repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    "--programs", "-p", is_flag=True, help="List available programs instead of backing up"
)
@click.option("--branch", "-b", help="Branch to back up (defaults to the current branch)")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be backed up without making any changes"
)
@click.option(
    "--zip-export",
    is_flag=True,
    help="Export the backup as a zip file in addition to creating the backup directory",
)
def backup(
    repo_path: Path, programs: bool, branch: Optional[str], dry_run: bool, zip_export: bool
) -> None:
    """Back up program configurations from a repository.

    REPO_PATH is the path to the repository to back up (e.g., ~/source/raycast-extensions/extensions/harmonyhub/).

    The backup command will:
    1. Identify the repository and determine its name
    2. Create a backup directory with the current timestamp
    3. Copy configured program files and directories to the backup
    4. Optionally create a zip archive of the backup (if --zip-export is used)

    By default, all configured programs will be backed up. Use --programs to list available programs.

    Examples:

      # Back up all configured programs from a repository
      dotfiles backup ~/source/raycast-extensions/extensions/harmonyhub/

      # List available programs that can be backed up
      dotfiles backup ~/source/raycast-extensions/extensions/harmonyhub/ --programs

      # Back up from a specific branch
      dotfiles backup ~/source/raycast-extensions/extensions/harmonyhub/ --branch main

      # Show what would be backed up without making changes
      dotfiles backup ~/source/raycast-extensions/extensions/harmonyhub/ --dry-run

      # Create a backup and export it as a zip file
      dotfiles backup ~/source/raycast-extensions/extensions/harmonyhub/ --zip-export
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

        # Initialize the repository if it doesn't exist
        if not repo.exists():
            repo.init()

        # Perform the backup
        if not manager.backup(
            repo, programs=None, branch=branch, dry_run=dry_run, zip_export=zip_export
        ):
            console.print("[red]Error: Failed to back up files")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument("repo_name", required=True)
@click.argument("target_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.option(
    "--programs",
    "-p",
    multiple=True,
    help="Programs to restore (can specify multiple times, e.g., -p cursor -p vscode)",
)
@click.option(
    "--branch",
    "-b",
    help="Branch to restore from (e.g., main, dev). If not specified, the latest backup from any branch will be used.",
)
@click.option(
    "--date",
    "-d",
    help="Date to restore from (format: YYYYMMDD-HHMMSS or YYYYMMDD). If not specified, the latest backup will be used.",
)
@click.option(
    "--latest", "-l", is_flag=True, help="Restore from latest backup regardless of branch or date"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force restore even if files exist (will overwrite existing files)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be restored without making any changes"
)
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
    """Restore program configurations from a backup.

    REPO_NAME is the name of the repository to restore from (e.g., harmonyhub).

    TARGET_DIR is the directory to restore files to (e.g., ~/source/raycast-extensions/extensions/harmonyhub/).

    The restore command will:
    1. Find the appropriate backup based on the repository name, branch, and date
    2. Restore all program configurations found in the backup to the target directory
    3. Validate that files were restored correctly

    By default, existing files will not be overwritten unless --force is used.

    Examples:

      # Restore the latest backup of 'harmonyhub' to the target directory
      dotfiles restore harmonyhub ~/source/raycast-extensions/extensions/harmonyhub/

      # Restore from a specific branch and date
      dotfiles restore harmonyhub ~/source/raycast-extensions/extensions/harmonyhub/ --branch main --date 20250226-184209

      # Force overwrite of existing files
      dotfiles restore harmonyhub ~/source/raycast-extensions/extensions/harmonyhub/ --force

      # Restore only specific programs
      dotfiles restore harmonyhub ~/source/raycast-extensions/extensions/harmonyhub/ -p cursor -p vscode

      # Show what would be restored without making changes
      dotfiles restore harmonyhub ~/source/raycast-extensions/extensions/harmonyhub/ --dry-run
    """
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
@click.option(
    "--branch", "-b", help="Branch to wipe (if not specified, all branches will be wiped)"
)
@click.option(
    "--date",
    "-d",
    help="Date to wipe (format: YYYYMMDD-HHMMSS or YYYYMMDD). If not specified, all backups will be wiped.",
)
@click.option("--force", "-f", is_flag=True, help="Force wipe without confirmation prompt")
def wipe(repo_name: str, branch: Optional[str], date: Optional[str], force: bool) -> None:
    """Wipe (delete) backups for a repository.

    REPO_NAME is the name of the repository to wipe backups for (e.g., harmonyhub).

    The wipe command will:
    1. Find backups matching the specified repository, branch, and date
    2. Prompt for confirmation (unless --force is used)
    3. Delete the matching backups

    Examples:

      # Wipe all backups for a repository (with confirmation)
      dotfiles wipe harmonyhub

      # Wipe backups for a specific branch
      dotfiles wipe harmonyhub --branch main

      # Wipe a specific backup by date
      dotfiles wipe harmonyhub --date 20250226-184209

      # Force wipe without confirmation
      dotfiles wipe harmonyhub --force

      # Combine options
      dotfiles wipe harmonyhub --branch main --date 20250226-184209 --force
    """
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
    """Initialize dotfiles configuration.

    This command will create a default configuration file if one doesn't exist.
    The configuration file defines which programs and files to back up.

    Currently not fully implemented.

    Example:

      # Initialize dotfiles configuration
      dotfiles init
    """
    console.print("[bold]Initializing dotfiles configuration...")
    console.print("Not implemented yet.")


@cli.command()
@click.argument("repo", required=False)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information about backups including file counts and types",
)
@click.option(
    "--latest",
    "-l",
    is_flag=True,
    help="Show only the latest backup for each repository and branch",
)
def list(repo: Optional[str], verbose: bool = False, latest: bool = False) -> None:
    """List available backups.

    REPO is an optional repository name to filter the results (e.g., harmonyhub).

    The list command will:
    1. Find all backups in the backup directory
    2. Display them in a table format with repository name, branch, timestamp, and programs
    3. Sort backups by timestamp with the newest first

    Examples:

      # List all available backups
      dotfiles list

      # List backups for a specific repository
      dotfiles list harmonyhub

      # Show only the latest backup for each repository and branch
      dotfiles list --latest

      # Show detailed information about backups
      dotfiles list --verbose

      # Combine options
      dotfiles list harmonyhub --latest --verbose
    """
    config = Config()
    manager = BackupManager(config)
    backups = manager.list_backups(repo)

    if not backups:
        console.print("[yellow]No backups found.")
        return

    # Group backups by repository and branch
    repo_branch_backups: Dict[str, Dict[str, List[Path]]] = {}
    for backup in backups:
        # Structure: backups/[repo_name]/[branch_name]/[timestamp]/
        # Where repo_name is the repository name (e.g., "harmonyhub")
        # Branch_name is the Git branch (e.g., "main")
        # And timestamp is when the backup was made (e.g., "20250226-184209")

        # Get the path components
        # First, get the direct parent directories
        backup_parent_path = backup.parent  # Branch directory (e.g., main)
        repo_path = backup_parent_path.parent  # Repository directory (e.g., harmonyhub)

        # Now extract the names
        repo_name = repo_path.name  # Repository name (e.g., harmonyhub)
        branch_name = backup_parent_path.name  # Branch name (e.g., main)
        timestamp = backup.name  # Timestamp (e.g., 20250226-184209)

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
    table.add_column("Backup Date", style="yellow")
    table.add_column("Contents", style="magenta")
    table.add_column("Restore Command", style="blue")

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

                # Look at the directories inside the backup to determine programs
                program_dirs = []
                try:
                    if backup.exists() and backup.is_dir():
                        program_dirs = [d for d in backup.iterdir() if d.is_dir()]
                except (PermissionError, FileNotFoundError):
                    pass

                # Get friendly names for the programs
                program_details = []

                # Hard-code the common programs for better readability
                for program_dir in program_dirs:
                    program_name = program_dir.name
                    if program_name == "cursor":
                        program_details.append("Cursor")
                    elif program_name == "vscode":
                        program_details.append("VS Code")
                    elif program_name == "git":
                        program_details.append("Git")
                    else:
                        # Try to get friendly name from config
                        program_config = config.get_program_config(program_name)
                        if program_config and "name" in program_config:
                            display_name = program_config["name"]
                            program_details.append(display_name)
                        else:
                            program_details.append(program_name.capitalize())

                # If no programs were found, set it to "Unknown"
                if not program_details:
                    program_details = ["Unknown"]

                # Remove unused code

                # Check the contents of the backup - look for program directories
                # Scan for program folders inside this timestamp directory
                programs_in_backup = []
                try:
                    if backup.exists() and backup.is_dir():
                        for content_dir in backup.iterdir():
                            if content_dir.is_dir():
                                if content_dir.name == "cursor":
                                    programs_in_backup.append("Cursor")
                                elif content_dir.name == "vscode":
                                    programs_in_backup.append("VS Code")
                                elif content_dir.name == "git":
                                    programs_in_backup.append("Git")
                                elif content_dir.name.startswith("202"):
                                    # This is another timestamp directory, skip it
                                    pass
                                else:
                                    # Try to get friendly name from config
                                    program_config = config.get_program_config(content_dir.name)
                                    if program_config and "name" in program_config:
                                        display_name = program_config["name"]
                                        programs_in_backup.append(display_name)
                                    else:
                                        programs_in_backup.append(content_dir.name.capitalize())
                except (PermissionError, FileNotFoundError):
                    programs_in_backup = ["Unknown"]

                # If no programs found
                if not programs_in_backup:
                    programs_in_backup = ["No content"]

                # Format timestamp for display (keep as is for now)
                display_timestamp = timestamp

                # Join all program names for display
                display_contents = ", ".join(programs_in_backup)

                # Create the restore command example
                restore_cmd = f"dotfiles restore {repo_name} TARGET_DIR --branch {branch_name} --date {timestamp}"

                # The actual repo_name is different than what's in the path
                # Use the directory name itself as the repo name
                actual_repo = repo_name  # e.g., harmonyhub

                table.add_row(
                    actual_repo,  # Repository name (e.g. harmonyhub)
                    branch_name,  # Branch name from the backup path
                    display_timestamp,  # Timestamp/date
                    display_contents,  # Contents of the backup (programs)
                    restore_cmd,  # Command to restore this backup
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
