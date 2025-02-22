"""Tests for bootstrap functionality."""

import shutil
from pathlib import Path

import pytest

from dotfiles.core.bootstrap import BootstrapManager
from dotfiles.core.repository import GitRepository


@pytest.fixture
def template_backup(bootstrap_manager: BootstrapManager, temp_git_repo: Path) -> Path:
    """Create a template backup for testing."""
    # Create test files in the repository
    cursor_dir = temp_git_repo / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "rules").mkdir()
    (cursor_dir / "rules" / "test.mdc").write_text("test")
    (cursor_dir / ".cursorrules").write_text("test")

    vscode_dir = temp_git_repo / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text('{"test": true}')
    (vscode_dir / "extensions.json").write_text('{"recommendations": []}')

    (temp_git_repo / ".gitconfig").write_text("[user]\n\tname = Test User")
    (temp_git_repo / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Create backup
    repo = GitRepository(temp_git_repo)
    bootstrap_manager.backup_manager.backup(repo)

    # Get the backup path
    backups = bootstrap_manager.backup_manager.list_backups(repo.name)
    assert len(backups) == 1
    return Path(backups[0])


def test_list_templates_empty(bootstrap_manager: BootstrapManager) -> None:
    """Test listing templates when none exist."""
    # Clean up any existing backups
    if bootstrap_manager.backup_manager.backup_dir.exists():
        shutil.rmtree(bootstrap_manager.backup_manager.backup_dir)
    assert not bootstrap_manager.list_templates()


def test_list_templates(bootstrap_manager: BootstrapManager, template_backup: Path) -> None:
    """Test listing templates."""
    templates = bootstrap_manager.list_templates()
    assert len(templates) == 1
    assert templates[0] == template_backup


def test_bootstrap_no_template(bootstrap_manager: BootstrapManager, temp_git_repo: Path) -> None:
    """Test bootstrap with no template."""
    repo = GitRepository(temp_git_repo)
    assert not bootstrap_manager.bootstrap(repo)


def test_bootstrap_with_template(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap with template."""
    repo = GitRepository(temp_git_repo)

    # Bootstrap from template
    assert bootstrap_manager.bootstrap(repo, template=template_backup)

    # Verify cursor files
    assert (temp_git_repo / ".cursor" / ".cursorrules").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".gitconfig").exists()

    # Verify file contents
    assert (temp_git_repo / ".cursor" / ".cursorrules").read_text() == "test"
    assert (temp_git_repo / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert (temp_git_repo / ".gitconfig").read_text() == "[user]\n\tname = Test User"


def test_bootstrap_specific_program(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap with specific program."""
    repo = GitRepository(temp_git_repo)

    # Bootstrap only vscode
    assert bootstrap_manager.bootstrap(repo, template=template_backup, programs=["vscode"])

    # Verify only vscode was bootstrapped
    assert not (temp_git_repo / ".cursor").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert not (temp_git_repo / ".gitconfig").exists()


def test_bootstrap_target_path(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap with target path."""
    repo = GitRepository(temp_git_repo)
    target_path = "extensions/test-extension"

    # Bootstrap into target path
    assert bootstrap_manager.bootstrap(repo, template=template_backup, target_path=target_path)

    # Verify files were created in target path
    target_dir = temp_git_repo / target_path
    assert (target_dir / ".cursor" / ".cursorrules").exists()
    assert (target_dir / ".vscode" / "settings.json").exists()
    assert (target_dir / ".gitconfig").exists()

    # Verify file contents
    assert (target_dir / ".cursor" / ".cursorrules").read_text() == "test"
    assert (target_dir / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert (target_dir / ".gitconfig").read_text() == "[user]\n\tname = Test User"

    # Verify Git was not initialized in target path (only root gets Git init)
    assert not (target_dir / ".git").exists()
    assert not (target_dir / ".git" / "config").exists()


def test_bootstrap_target_path_with_program(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap with target path and specific program."""
    repo = GitRepository(temp_git_repo)
    target_path = "extensions/test-extension"

    # Bootstrap only vscode into target path
    assert bootstrap_manager.bootstrap(
        repo, template=template_backup, target_path=target_path, programs=["vscode"]
    )

    # Verify only vscode was bootstrapped in target path
    target_dir = temp_git_repo / target_path
    assert not (target_dir / ".cursor").exists()
    assert (target_dir / ".vscode" / "settings.json").exists()
    assert (target_dir / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert not (target_dir / ".gitconfig").exists()


def test_bootstrap_target_path_nested(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap with deeply nested target path."""
    repo = GitRepository(temp_git_repo)
    target_path = "extensions/category/subcategory/test-extension"

    # Bootstrap into nested target path
    assert bootstrap_manager.bootstrap(repo, template=template_backup, target_path=target_path)

    # Verify files were created in nested target path
    target_dir = temp_git_repo / target_path
    assert (target_dir / ".cursor" / ".cursorrules").exists()
    assert (target_dir / ".vscode" / "settings.json").exists()
    assert (target_dir / ".gitconfig").exists()

    # Verify file contents
    assert (target_dir / ".cursor" / ".cursorrules").read_text() == "test"
    assert (target_dir / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert (target_dir / ".gitconfig").read_text() == "[user]\n\tname = Test User"


def test_bootstrap_target_path_exists(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap into existing target path."""
    repo = GitRepository(temp_git_repo)
    target_path = "extensions/test-extension"

    # Create target directory with existing file
    target_dir = temp_git_repo / target_path
    target_dir.mkdir(parents=True)
    (target_dir / "existing.txt").write_text("existing content")

    # Bootstrap into target path
    assert bootstrap_manager.bootstrap(repo, template=template_backup, target_path=target_path)

    # Verify existing file was preserved
    assert (target_dir / "existing.txt").exists()
    assert (target_dir / "existing.txt").read_text() == "existing content"

    # Verify new files were added
    assert (target_dir / ".cursor" / ".cursorrules").exists()
    assert (target_dir / ".vscode" / "settings.json").exists()
    assert (target_dir / ".gitconfig").exists()


def test_bootstrap_dry_run(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path, template_backup: Path
) -> None:
    """Test bootstrap dry run."""
    repo = GitRepository(temp_git_repo)

    # Perform bootstrap
    assert bootstrap_manager.bootstrap(repo, template=template_backup)

    # Verify files were created
    assert (temp_git_repo / ".cursor" / ".cursorrules").exists()
    assert (temp_git_repo / ".vscode" / "settings.json").exists()
    assert (temp_git_repo / ".gitconfig").exists()

    # Verify file contents
    assert (temp_git_repo / ".cursor" / ".cursorrules").read_text() == "test"
    assert (temp_git_repo / ".vscode" / "settings.json").read_text() == '{"test": true}'
    assert (temp_git_repo / ".gitconfig").read_text() == "[user]\n\tname = Test User"


def test_bootstrap_nonexistent_template(
    bootstrap_manager: BootstrapManager, temp_git_repo: Path
) -> None:
    """Test bootstrap with nonexistent template."""
    repo = GitRepository(temp_git_repo)
    template = Path("nonexistent/template")
    assert not bootstrap_manager.bootstrap(repo, template=template)
