"""Command implementations for dotfiles CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from .backup import BackupManager
from .bootstrap import BootstrapManager
from .config import Config
from .migrate import MigrateManager
from .repository import RepositoryManager
from .restore import RestoreManager
from .wipe import WipeManager

console = Console()


def list_repos(args: argparse.Namespace, config: Config) -> int:
    """List available repositories."""
    repo_manager = RepositoryManager(config)
    repos = repo_manager.list_repositories()

    if not repos:
        console.print("No repositories found in configured search paths.")
        return 0

    for repo in repos:
        console.print(f"[bold]{repo.name}[/]")
        console.print(f"  Path: {repo.path}")
        console.print(f"  Branch: {repo.get_current_branch()}")
        console.print()

    return 0


def list_backups(args: argparse.Namespace, config: Config) -> int:
    """List available backups."""
    backup_manager = BackupManager(config)
    backups = backup_manager.list_backups(args.repo)

    if not backups:
        console.print("No backups found.")
        return 0

    # Group backups by repository
    repo_backups: dict[str, list[tuple[Path, str, str | None]]] = {}
    for backup in backups:
        # Handle legacy structure
        if backup.name.endswith(".legacy"):
            repo_name = backup.name.replace(".legacy", "")
            if repo_name not in repo_backups:
                repo_backups[repo_name] = []
            repo_backups[repo_name].append((backup, "legacy", None))
        else:
            # New structure
            repo_name = backup.parent.parent.name
            branch = backup.parent.name
            if repo_name not in repo_backups:
                repo_backups[repo_name] = []
            repo_backups[repo_name].append((backup, branch, backup.name))

    # Display backups organized by repository
    for repo_name, repo_backup_list in sorted(repo_backups.items()):
        console.print(f"\n[bold blue]{repo_name}[/]")
        for backup, branch, timestamp in repo_backup_list:
            if branch == "legacy":
                console.print("  [yellow]Legacy Backup[/]")
            else:
                console.print(f"  [green]{branch}[/] - {timestamp}")

            # List program contents
            for program_dir in backup.iterdir():
                if program_dir.is_dir() and program_dir.name in config.programs:
                    console.print(f"    {program_dir.name}")
                    # List files in program directory
                    for item in program_dir.iterdir():
                        if item.is_file():
                            console.print(f"      {item.name}")
            console.print()

    return 0


def backup(args: argparse.Namespace, config: Config) -> int:
    """Backup configurations."""
    repo_manager = RepositoryManager(config)
    backup_manager = BackupManager(config)

    # Get repository
    if args.repo:
        repo = repo_manager.get_repository(args.repo)
        if not repo:
            console.print(f"Error: Repository not found: {args.repo}")
            return 1
        repos = [repo]
    else:
        repos = repo_manager.list_repositories()
        if not repos:
            console.print("No repositories found in configured search paths.")
            return 1

    # Backup each repository
    success = True
    for repo in repos:
        console.print(f"[bold]Backing up {repo.name}[/]")
        try:
            if not backup_manager.backup(
                repo,
                programs=[args.program] if args.program else None,
                branch=args.branch,
                dry_run=args.dry_run,
            ):
                console.print(f"Warning: No configurations backed up for {repo.name}")
                success = False
        except Exception as e:
            console.print(f"Error backing up {repo.name}: {e}")
            success = False

    return 0 if success else 1


def restore(args: argparse.Namespace, config: Config) -> int:
    """Restore configurations."""
    repo_manager = RepositoryManager(config)
    backup_manager = BackupManager(config)
    backup_manager.backup_dir = Path(
        getattr(args, "backup_dir", "backups")
    )  # Use backup_dir from args
    restore_manager = RestoreManager(config, backup_manager)

    try:
        repo = repo_manager.get_repository(args.repo)
        if not repo:
            console.print(f"[red]Error: Repository not found: {args.repo}")
            return 1

        if restore_manager.restore(
            repo,
            programs=[args.program] if args.program else None,
            branch=args.branch,
            dry_run=getattr(args, "dry_run", False),
            force=getattr(args, "force", False),
        ):
            return 0
        return 1
    except Exception as e:
        console.print(f"[red]Error during restore: {e}")
        return 1


def bootstrap(args: argparse.Namespace, config: Config) -> int:
    """Bootstrap a repository."""
    repo_manager = RepositoryManager(config)
    bootstrap_manager = BootstrapManager(config)
    bootstrap_manager.backup_manager.backup_dir = Path(
        getattr(args, "backup_dir", "backups")
    )  # Use backup_dir from args

    try:
        repo = repo_manager.get_repository(args.repo)
        if not repo:
            console.print(f"[red]Error: Repository not found: {args.repo}")
            return 1

        if bootstrap_manager.bootstrap(
            repo,
            template=args.template,
            programs=[args.program] if args.program else None,
            target_path=args.target_path,
        ):
            return 0
        return 1
    except Exception as e:
        console.print(f"[red]Error during bootstrap: {e}")
        return 1


def wipe(args: argparse.Namespace, config: Config) -> int:
    """Wipe configurations."""
    repo_manager = RepositoryManager(config)
    wipe_manager = WipeManager(config)

    # Get repository
    if args.repo:
        repo = repo_manager.get_repository(args.repo)
        if not repo:
            console.print(f"Error: Repository not found: {args.repo}")
            return 1
        repos = [repo]
    else:
        repos = repo_manager.list_repositories()
        if not repos:
            console.print("No repositories found in configured search paths.")
            return 1

    # Wipe each repository
    success = True
    for repo in repos:
        console.print(f"[bold]Wiping {repo.name}[/]")
        try:
            if not wipe_manager.wipe(
                repo,
                programs=[args.program] if args.program else None,
                dry_run=args.dry_run,
                force=args.force,
            ):
                console.print(f"Warning: No configurations wiped for {repo.name}")
                success = False
        except Exception as e:
            console.print(f"Error wiping {repo.name}: {e}")
            success = False

    return 0 if success else 1


def migrate(args: argparse.Namespace, config: Config) -> int:
    """Migrate legacy backups to new format."""
    migrate_manager = MigrateManager(config)

    try:
        repos = [args.repo] if args.repo else None
        if migrate_manager.migrate(repos=repos, branch=args.branch, dry_run=args.dry_run):
            return 0
        return 1
    except Exception as e:
        console.print(f"[red]Error during migration: {e}[/]")
        return 1


COMMANDS = {
    "list": {
        "repos": list_repos,
        "backups": list_backups,
    },
    "backup": backup,
    "restore": restore,
    "bootstrap": bootstrap,
    "wipe": wipe,
    "migrate": migrate,
}
