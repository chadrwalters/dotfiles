"""Repository functionality for dotfiles."""

import subprocess
from pathlib import Path
from typing import List


class GitRepository:
    """Represents a Git repository."""

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
        """Initialize a new Git repository."""
        self._run_git("init")
        # Configure Git for testing
        self._run_git("config", "user.name", "Test User")
        self._run_git("config", "user.email", "test@example.com")
        # Create initial commit to establish main branch
        readme = self.path / "README.md"
        readme.write_text("# Test Repository\n")
        self.add("README.md")
        self.commit("Initial commit")

    def add(self, path: str) -> None:
        """Add files to Git staging area."""
        self._run_git("add", path)

    def commit(self, message: str) -> None:
        """Commit staged changes."""
        try:
            self._run_git("commit", "-m", message)
        except RuntimeError as e:
            if "nothing to commit" in str(e):
                return
            raise

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        except RuntimeError:
            # If no commits yet, return default branch name
            return "main"

    def list_branches(self) -> List[str]:
        """List all branches."""
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
