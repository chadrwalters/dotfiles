"""Command-line interface for dotfiles management."""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict, List, Optional, Union, cast

from rich.console import Console

from .core.commands import COMMANDS
from .core.config import Config

console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Dotfiles management system for development configurations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser("list", help="List repositories or backups")
    list_parser.add_argument(
        "type",
        choices=["repos", "backups"],
        help="Type of items to list",
    )
    list_parser.add_argument("--repo", help="Filter backups by repository name")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup configurations")
    backup_parser.add_argument("--repo", help="Source repository")
    backup_parser.add_argument("--program", help="Specific program to backup")
    backup_parser.add_argument("--branch", help="Specific branch to backup from")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore configurations")
    restore_parser.add_argument("--repo", help="Target repository")
    restore_parser.add_argument("--program", help="Specific program to restore")
    restore_parser.add_argument("--branch", help="Specific branch to restore to")

    # Bootstrap command
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Bootstrap a new repository")
    bootstrap_parser.add_argument("--repo", help="Repository to bootstrap")
    bootstrap_parser.add_argument("--template", help="Template backup to use")
    bootstrap_parser.add_argument(
        "--target-path", help="Target path within the repository to bootstrap into"
    )
    bootstrap_parser.add_argument("--program", help="Specific program to bootstrap")

    # Wipe command
    wipe_parser = subparsers.add_parser("wipe", help="Wipe configurations")
    wipe_parser.add_argument("--repo", help="Repository to wipe")
    wipe_parser.add_argument("--program", help="Specific program to wipe")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate legacy backups to new format")
    migrate_parser.add_argument("--repo", help="Specific repository to migrate")
    migrate_parser.add_argument("--branch", default="main", help="Branch to migrate backups to")
    migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be migrated without making changes"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the dotfiles CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        config = Config()
        errors = config.validate()
        if errors:
            console.print("[bold red]Configuration errors:[/]")
            for error in errors:
                console.print(f"  - {error}")
            return 1

        # Define command function type
        CommandFunc = Callable[[argparse.Namespace, Config], int]
        ListCommands = Dict[str, CommandFunc]
        Commands = Dict[str, Union[ListCommands, CommandFunc]]

        # Cast COMMANDS to the correct type
        commands = cast(Commands, COMMANDS)

        if args.command == "list":
            list_commands = commands["list"]
            if not isinstance(list_commands, dict):
                console.print("[red]Error: Invalid command configuration[/]")
                return 1
            list_type = args.type
            if list_type not in list_commands:
                console.print(f"[red]Error: Invalid list type: {list_type}[/]")
                return 1
            list_func = list_commands[list_type]
            return list_func(args, config)
        else:
            command_func = commands.get(args.command)
            if command_func is None:
                console.print(f"[red]Error: Invalid command: {args.command}[/]")
                return 1
            if isinstance(command_func, dict):
                console.print("[red]Error: Invalid command handler[/]")
                return 1
            return command_func(args, config)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
        return 130
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
