"""Repository functionality for dotfiles."""

import subprocess
from pathlib import Path
from typing import List


class GitRepository:
    """Represents a Git repository for managing Cursor configuration files.

    This class provides functionality for interacting with Git repositories,
    specifically focused on managing Cursor IDE configuration files. It handles
    basic Git operations like initialization, adding files, committing changes,
    and branch management.

    Attributes:
        path (Path): Path to the Git repository.
    """

    def __init__(self, path: Path):
        """Initialize repository."""
        self.path = Path(path).resolve()
        self.name = self.path.name

    def __str__(self) -> str:
        """Return string representation."""
        return f"GitRepository({self.path})"

    def __repr__(self) -> str:
        """Return string representation."""
        return self.__str__()

    def exists(self) -> bool:
        """Check if repository exists and is a Git repository."""
        if not self.path.exists() or not self.path.is_dir():
            return False
        try:
            self._run_git("rev-parse", "--git-dir")
            return True
        except RuntimeError:
            return False

    def _run_git(self, *args: str) -> str:
        """Run a Git command and return its output."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if e.stderr:
                raise RuntimeError(f"Git command failed: {e.stderr.strip()}")
            if e.stdout:
                raise RuntimeError(f"Git command failed: {e.stdout.strip()}")
            raise RuntimeError("Git command failed with no output")

    def init(self) -> None:
        """Initialize a new Git repository for Cursor configuration management.

        Creates a new Git repository at the specified path if it doesn't exist,
        sets up basic Git configuration, and creates an initial commit.

        The initialization process:
        1. Creates the repository directory if needed
        2. Initializes Git repository
        3. Configures Git user settings for testing
        4. Creates a README.md file
        5. Makes initial commit
        6. Ensures main branch is set up

        Raises:
            RuntimeError: If Git operations fail during initialization.
        """
        if not self.path.exists():
            self.path.mkdir(parents=True)

        # Initialize Git repository
        self._run_git("init")

        # Configure Git for testing
        self._run_git("config", "user.name", "Test User")
        self._run_git("config", "user.email", "test@example.com")

        # Create README.md file
        readme = self.path / "README.md"
        readme.write_text("# Test Repository\n")

        # Add all files and create initial commit
        self._run_git("add", ".")
        self._run_git("commit", "-m", "Initial commit")

        # Ensure we're on main branch
        try:
            self._run_git("branch", "-M", "main")
        except RuntimeError:
            pass  # Branch already exists

    def add(self, path: str) -> None:
        """Add Cursor configuration files to Git staging area.

        Args:
            path (str): Path to the file or directory to add, relative to repository root.

        Raises:
            RuntimeError: If Git add operation fails.
        """
        self._run_git("add", path)

    def commit(self, message: str) -> None:
        """Commit staged Cursor configuration changes.

        Args:
            message (str): Commit message describing the changes.

        Raises:
            RuntimeError: If Git commit operation fails for reasons other than
                        nothing to commit.

        Note:
            If there are no changes to commit, this method will return silently
            instead of raising an error.
        """
        try:
            self._run_git("commit", "-m", message)
        except RuntimeError as e:
            if "nothing to commit" in str(e):
                return
            raise

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            str: Name of the current branch.

        Raises:
            RuntimeError: If Git branch lookup fails.

        Example:
            ```python
            repo = GitRepository("/path/to/repo")
            branch = repo.get_current_branch()
            print(f"Current branch: {branch}")  # e.g. "main"
            ```
        """
        return self._run_git("rev-parse", "--abbrev-ref", "HEAD")

    def list_branches(self) -> List[str]:
        """List all branches in the repository.

        Returns:
            List[str]: List of branch names, with leading whitespace and
                      decorators (like '*') removed.

        Raises:
            RuntimeError: If Git branch listing fails.

        Example:
            ```python
            repo = GitRepository("/path/to/repo")
            branches = repo.list_branches()
            print("Available branches:", branches)  # e.g. ["main", "develop"]
            ```
        """
        output = self._run_git("branch", "--list")
        return [line.strip("* ") for line in output.splitlines()]

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            self._run_git("diff", "--quiet", "HEAD")
            return False
        except RuntimeError:
            return True

    def stash_save(self) -> None:
        """Save changes to stash."""
        self._run_git("stash", "save")

    def stash_pop(self) -> None:
        """Pop changes from stash."""
        self._run_git("stash", "pop")

    def switch_branch(self, branch: str) -> None:
        """Switch to a different branch."""
        try:
            # Try to switch to existing branch
            self._run_git("checkout", branch)
        except RuntimeError:
            # Branch doesn't exist, create it
            self._run_git("checkout", "-b", branch)

    def create_branch(self, branch: str) -> None:
        """Create a new branch."""
        self._run_git("checkout", "-b", branch)
