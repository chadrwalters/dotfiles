"""Test CLI commands."""

import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from dotfiles.cli import cli
from dotfiles.core.repository import GitRepository


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a CLI runner."""
    return CliRunner()


@pytest.fixture
def test_repo(tmp_path: Path) -> GitRepository:
    """Create a test repository."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    # Create some files
    vscode_dir = repo_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text('{"foo": "bar"}')
    (vscode_dir / "extensions.json").write_text('{"extensions": []}')
    (repo_path / ".gitconfig").write_text("[user]\n\tname = Test User")
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/")
    cursor_dir = repo_path / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "settings.json").write_text('{"cursor": "settings"}')
    return GitRepository(repo_path)


def test_backup(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test backup command."""
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0
    assert "Backing up" in result.output


def test_backup_missing_dir(cli_runner: CliRunner) -> None:
    """Test backup command with missing directory."""
    result = cli_runner.invoke(cli, ["backup", "/path/does/not/exist"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_restore_missing_backup(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test restore command with missing backup."""
    result = cli_runner.invoke(cli, ["restore", "nonexistent", str(tmp_path)])
    assert result.exit_code == 1
    assert "No backups found" in result.output


def test_restore(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test restore command."""
    # First create a backup
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Then restore it
    result = cli_runner.invoke(cli, ["restore", test_repo.name, str(test_repo.path)])
    assert result.exit_code == 0
    # Check for either "Restored files" or "All files restored successfully" in the output
    assert any(
        msg in result.output for msg in ["Restored files", "All files restored successfully"]
    )


def test_list_command(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test list command."""
    # First create a backup
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Then list backups
    result = cli_runner.invoke(cli, ["list"])
    assert result.exit_code == 0

    # Print the output for debugging
    print("\nTEST LIST OUTPUT:")
    print(result.output)

    # Verify the output has the expected columns - only check for basic columns that we know will be there
    assert "Repository" in result.output
    assert "Branch" in result.output
    assert "Backup Date" in result.output
    assert "Contents" in result.output

    # Verify the content of rows - check for the repo name which should be in the output
    assert test_repo.name in result.output

    # Test the --latest flag
    result = cli_runner.invoke(cli, ["list", "--latest"])
    assert result.exit_code == 0
    assert "Repository" in result.output


def test_backup_with_zip_export(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test backup command with zip export."""
    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])
    assert result.exit_code == 0
    assert "Backing up" in result.output
    assert "Creating zip archive" in result.output
    assert "Successfully created zip archive" in result.output

    # Verify zip file exists and is valid
    backup_dir = Path("backups") / test_repo.name / test_repo.get_current_branch()
    latest_backup = sorted(backup_dir.iterdir())[-1]
    zip_path = latest_backup.with_suffix(".zip")

    assert zip_path.exists()

    # Verify zip file is valid and contains expected files
    with zipfile.ZipFile(zip_path) as zf:
        # Should have at least one file
        assert len(zf.namelist()) > 0
        # All files should be readable
        assert all(zf.testzip() is None for _ in [None])


def test_backup_with_zip_export_dry_run(cli_runner: CliRunner, test_repo: GitRepository) -> None:
    """Test backup command with zip export in dry run mode."""
    # Run backup with zip export in dry run mode
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export", "--dry-run"])
    assert result.exit_code == 0
    assert "Backing up" in result.output
    assert "Would backup:" in result.output

    # Verify no zip file was created
    backup_dir = Path("backups") / test_repo.name / test_repo.get_current_branch()
    if backup_dir.exists():  # Directory might not exist in dry run
        latest_backup = sorted(backup_dir.iterdir())[-1] if list(backup_dir.iterdir()) else None
        if latest_backup:
            zip_path = latest_backup.with_suffix(".zip")
            assert not zip_path.exists()


def test_backup_with_zip_export_large_files(
    cli_runner: CliRunner, test_repo: GitRepository
) -> None:
    """Test backup command with zip export for large files."""
    # Create a large file (1MB)
    large_file = test_repo.path / ".cursor" / "large_file.bin"
    large_file.write_bytes(b"0" * (1024 * 1024))

    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])
    assert result.exit_code == 0
    assert "Backing up" in result.output
    assert "Creating zip archive" in result.output
    assert "Successfully created zip archive" in result.output

    # Verify zip file exists and contains the large file
    backup_dir = Path("backups") / test_repo.name / test_repo.get_current_branch()
    latest_backup = sorted(backup_dir.iterdir())[-1]
    zip_path = latest_backup.with_suffix(".zip")

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        assert "large_file.bin" in [Path(name).name for name in zf.namelist()]
        # Verify file size is preserved
        file_info = zf.getinfo(
            [name for name in zf.namelist() if Path(name).name == "large_file.bin"][0]
        )
        assert file_info.file_size == 1024 * 1024


def test_backup_with_zip_export_special_chars(
    cli_runner: CliRunner, test_repo: GitRepository
) -> None:
    """Test backup command with zip export for files with special characters."""
    # Create files with special characters
    special_files = [
        ".cursor/file with spaces.txt",
        ".cursor/file_with_unicode_🚀.txt",
        ".cursor/file_with_symbols_#@!.txt",
    ]

    for file_path in special_files:
        full_path = test_repo.path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("test content")

    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])
    assert result.exit_code == 0
    assert "Successfully created zip archive" in result.output

    # Verify zip file contains all files with correct names
    backup_dir = Path("backups") / test_repo.name / test_repo.get_current_branch()
    latest_backup = sorted(backup_dir.iterdir())[-1]
    zip_path = latest_backup.with_suffix(".zip")

    with zipfile.ZipFile(zip_path) as zf:
        file_names = [Path(name).name for name in zf.namelist()]
        assert "file with spaces.txt" in file_names
        assert "file_with_unicode_🚀.txt" in file_names
        assert "file_with_symbols_#@!.txt" in file_names


def test_backup_with_zip_export_nested_dirs(
    cli_runner: CliRunner, test_repo: GitRepository
) -> None:
    """Test backup command with zip export for deeply nested directories."""
    # Create nested directory structure
    nested_dir = test_repo.path / ".cursor" / "deep" / "nested" / "directory" / "structure"
    nested_dir.mkdir(parents=True)
    (nested_dir / "test.txt").write_text("test content")

    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])
    assert result.exit_code == 0
    assert "Successfully created zip archive" in result.output

    # Verify zip file preserves directory structure
    backup_dir = Path("backups") / test_repo.name / test_repo.get_current_branch()
    latest_backup = sorted(backup_dir.iterdir())[-1]
    zip_path = latest_backup.with_suffix(".zip")

    with zipfile.ZipFile(zip_path) as zf:
        assert any("deep/nested/directory/structure/test.txt" in name for name in zf.namelist())


def test_backup_with_zip_export_permission_error(
    cli_runner: CliRunner, test_repo: GitRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test backup command with zip export when permission error occurs."""

    def mock_mkdir(*args: object, **kwargs: object) -> None:
        raise PermissionError("Permission denied")

    # Create a backup first so we have a directory to work with
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path)])
    assert result.exit_code == 0

    # Mock mkdir to simulate permission error
    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])

    # The backup should still succeed even if zip creation fails
    assert result.exit_code == 0
    assert "Backup was successful but zip creation failed" in result.output


def test_backup_with_zip_export_disk_full(
    cli_runner: CliRunner, test_repo: GitRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test backup command with zip export when disk is full."""

    def mock_write(*args: object, **kwargs: object) -> None:
        raise OSError("No space left on device")

    # Mock ZipFile.write to simulate disk full error
    monkeypatch.setattr(zipfile.ZipFile, "write", mock_write)

    # Run backup with zip export
    result = cli_runner.invoke(cli, ["backup", str(test_repo.path), "--zip-export"])

    # The backup should still succeed even if zip creation fails
    assert result.exit_code == 0
    assert "Backup was successful but zip creation failed" in result.output
    assert "No space left on device" in result.output
