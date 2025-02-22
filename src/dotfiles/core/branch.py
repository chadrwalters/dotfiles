"""Branch management functionality."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, cast

from rich.console import Console

console = Console()


@dataclass
class StashEntry:
    """Represents a Git stash entry."""

    index: int
    message: str
    branch: str


class GitError(Exception):
    """Git error class."""

    def __init__(self, message: str, command: str, output: str) -> None:
        """Initialize error."""
        super().__init__(message)
        self.command = command
        self.output = output


def run_git_command(
    repo_path: Path,
    command: List[str],
    error_message: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command with proper error handling."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path)] + command,
            capture_output=True,
            text=True,
            check=check,
        )
        if check and result.returncode != 0:
            raise GitError(
                message=error_message,
                command=" ".join(["git"] + command),
                output=f"stdout: {result.stdout}\nstderr: {result.stderr}",
            )
        return cast(subprocess.CompletedProcess[str], result)
    except subprocess.CalledProcessError as e:
        raise GitError(
            message=error_message,
            command=" ".join(["git"] + command),
            output=f"stdout: {e.stdout}\nstderr: {e.stderr}",
        )


def get_current_branch(repo_path: Path) -> str:
    """Get current branch name."""
    result = run_git_command(
        repo_path,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        "Failed to get current branch",
    )
    return result.stdout.strip()


def list_branches(repo_path: Path) -> List[str]:
    """List available branches."""
    result = run_git_command(
        repo_path,
        ["branch", "--format=%(refname:short)"],
        "Failed to list branches",
    )
    return [branch for branch in result.stdout.splitlines() if branch]


def has_changes(repo_path: Path) -> bool:
    """Check if repository has uncommitted changes."""
    result = run_git_command(
        repo_path,
        ["status", "--porcelain"],
        "Failed to check repository status",
        check=False,
    )
    return bool(result.stdout.strip())


def stash_changes(repo_path: Path, message: str) -> bool:
    """Stash uncommitted changes."""
    if not has_changes(repo_path):
        return False

    # Add untracked files to index
    run_git_command(
        repo_path,
        ["add", "."],
        "Failed to add untracked files",
        check=False,
    )

    try:
        run_git_command(
            repo_path,
            ["stash", "push", "-m", message],
            "Failed to stash changes",
        )
        return True
    except GitError:
        return False


def list_stashes(repo_path: Path) -> List[str]:
    """List available stashes."""
    result = run_git_command(
        repo_path,
        ["stash", "list"],
        "Failed to list stashes",
        check=False,
    )
    return [stash for stash in result.stdout.splitlines() if stash]


def pop_stash(repo_path: Path) -> bool:
    """Pop stashed changes."""
    if not list_stashes(repo_path):
        return False

    try:
        run_git_command(
            repo_path,
            ["stash", "pop"],
            "Failed to pop stash",
            check=False,
        )
        return True
    except GitError:
        print("Error: Failed to restore stashed changes!")
        return False


def switch_branch(
    repo_path: Path, branch: str, create: bool = False, stash_message: Optional[str] = None
) -> bool:
    """Switch to a different branch."""
    try:
        # Check for uncommitted changes
        if has_changes(repo_path):
            if stash_message:
                if not stash_changes(repo_path, stash_message):
                    return False
            else:
                return False

        # Switch branch
        if create:
            result = run_git_command(
                repo_path,
                ["checkout", "-b", branch],
                f"Failed to create and switch to branch {branch}",
                check=False,
            )
        else:
            result = run_git_command(
                repo_path,
                ["checkout", branch],
                f"Failed to switch to branch {branch}",
                check=False,
            )

        if result.returncode != 0:
            return False

        # Pop stash if needed
        if stash_message and has_stash(repo_path):
            pop_stash(repo_path)

        return True
    except Exception:
        return False


def has_stash(repo_path: Path) -> bool:
    """Check if repository has stashed changes."""
    return bool(list_stashes(repo_path))
