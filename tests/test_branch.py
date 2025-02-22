"""Test branch management module."""

import subprocess
from pathlib import Path

from dotfiles.core.branch import (
    get_current_branch,
    has_changes,
    list_branches,
    list_stashes,
    pop_stash,
    stash_changes,
    switch_branch,
)


def test_get_current_branch(temp_git_repo: Path) -> None:
    """Test getting current branch name."""
    branch = get_current_branch(temp_git_repo)
    assert branch == "main"


def test_list_branches(temp_git_repo: Path) -> None:
    """Test listing branches."""
    # Create test branches
    subprocess.run(["git", "branch", "test1"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "branch", "test2"], cwd=temp_git_repo, check=True)

    branches = list_branches(temp_git_repo)
    assert len(branches) == 3
    assert "main" in branches
    assert "test1" in branches
    assert "test2" in branches


def test_has_changes(temp_git_repo: Path) -> None:
    """Test checking for uncommitted changes."""
    # No changes initially
    assert not has_changes(temp_git_repo)

    # Create a change
    (temp_git_repo / "change.txt").write_text("change")
    assert has_changes(temp_git_repo)

    # Stage the change
    subprocess.run(["git", "add", "change.txt"], cwd=temp_git_repo, check=True)
    assert has_changes(temp_git_repo)

    # Commit the change
    subprocess.run(["git", "commit", "-m", "test change"], cwd=temp_git_repo, check=True)
    assert not has_changes(temp_git_repo)


def test_stash_operations(temp_git_repo: Path) -> None:
    """Test stash operations."""
    # Create a change
    (temp_git_repo / "stash.txt").write_text("stash content")

    # Stash with message
    assert stash_changes(temp_git_repo, "test stash")

    # List stashes
    stashes = list_stashes(temp_git_repo)
    assert len(stashes) == 1
    assert "test stash" in stashes[0]

    # Pop stash
    assert pop_stash(temp_git_repo)
    assert not list_stashes(temp_git_repo)
    assert (temp_git_repo / "stash.txt").read_text() == "stash content"


def test_switch_branch(temp_git_repo: Path) -> None:
    """Test branch switching."""
    # Create and switch to new branch
    assert switch_branch(temp_git_repo, "feature", create=True)
    assert get_current_branch(temp_git_repo) == "feature"

    # Switch back to main
    assert switch_branch(temp_git_repo, "main")
    assert get_current_branch(temp_git_repo) == "main"


def test_switch_branch_with_changes(temp_git_repo: Path) -> None:
    """Test branch switching with uncommitted changes."""
    # Create a change
    (temp_git_repo / "switch.txt").write_text("switch content")

    # Switch to new branch
    assert switch_branch(temp_git_repo, "feature", create=True, stash_message="switching")
    assert get_current_branch(temp_git_repo) == "feature"

    # Verify file was restored
    assert (temp_git_repo / "switch.txt").read_text() == "switch content"


def test_switch_branch_failure(temp_git_repo: Path) -> None:
    """Test branch switching failure."""
    # Create a conflicting file
    (temp_git_repo / "conflict.txt").write_text("main content")
    subprocess.run(["git", "add", "conflict.txt"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "main commit"], cwd=temp_git_repo, check=True)

    # Create and switch to new branch
    subprocess.run(["git", "checkout", "-b", "conflict-branch"], cwd=temp_git_repo, check=True)
    (temp_git_repo / "conflict.txt").write_text("branch content")
    subprocess.run(["git", "add", "conflict.txt"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "branch commit"], cwd=temp_git_repo, check=True)

    # Switch back to main and modify the file
    original_branch = "master" if "master" in list_branches(temp_git_repo) else "main"
    subprocess.run(["git", "checkout", original_branch], cwd=temp_git_repo, check=True)
    (temp_git_repo / "conflict.txt").write_text("modified content")
    subprocess.run(["git", "add", "conflict.txt"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "modified commit"], cwd=temp_git_repo, check=True)

    # Modify the file again without committing
    (temp_git_repo / "conflict.txt").write_text("uncommitted changes")

    # Attempt to switch branch should fail
    assert not switch_branch(temp_git_repo, "conflict-branch"), "Expected switch_branch to fail"
