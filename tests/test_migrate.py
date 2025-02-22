"""Tests for migration functionality."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from dotfiles.core.commands import migrate
from dotfiles.core.config import Config
from dotfiles.core.migrate import MigrateManager


@pytest.fixture
def migrate_manager(test_config: Config) -> MigrateManager:
    """Create test migrate manager."""
    return MigrateManager(test_config)


def test_is_legacy_backup(migrate_manager: MigrateManager, temp_dir: Path) -> None:
    """Test legacy backup detection."""
    # Create a legacy backup structure
    backup_dir = temp_dir / "backups" / "testrepo"
    backup_dir.mkdir(parents=True)
    (backup_dir / "cursor").mkdir()
    (backup_dir / "vscode").mkdir()

    assert migrate_manager.is_legacy_backup(backup_dir)

    # Create a new-style backup structure
    new_backup_dir = temp_dir / "backups" / "newrepo" / "main" / "20240101-000000"
    new_backup_dir.mkdir(parents=True)
    (new_backup_dir / "cursor").mkdir()
    (new_backup_dir / "vscode").mkdir()

    assert not migrate_manager.is_legacy_backup(new_backup_dir.parent.parent)


def test_get_legacy_backups(migrate_manager: MigrateManager, temp_dir: Path) -> None:
    """Test getting legacy backups."""
    # Create legacy backup structure
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir(parents=True)

    # Legacy backup 1
    legacy1 = backup_dir / "testrepo1"
    legacy1.mkdir()
    (legacy1 / "cursor").mkdir()
    (legacy1 / "vscode").mkdir()

    # Legacy backup 2
    legacy2 = backup_dir / "testrepo2"
    legacy2.mkdir()
    (legacy2 / "cursor").mkdir()
    (legacy2 / "vscode").mkdir()

    # New-style backup
    new_backup = backup_dir / "newrepo" / "main" / "20240101-000000"
    new_backup.mkdir(parents=True)
    (new_backup / "cursor").mkdir()
    (new_backup / "vscode").mkdir()

    migrate_manager.backup_manager.backup_dir = backup_dir
    legacy_backups = migrate_manager.get_legacy_backups()
    assert len(legacy_backups) == 2
    assert legacy1 in legacy_backups
    assert legacy2 in legacy_backups


def test_migrate_backup(migrate_manager: MigrateManager, temp_dir: Path) -> None:
    """Test migrating a single backup."""
    # Create legacy backup structure
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir(parents=True)

    legacy = backup_dir / "testrepo"
    legacy.mkdir()
    (legacy / "cursor").mkdir()
    (legacy / "cursor" / "test.txt").write_text("test")
    (legacy / "vscode").mkdir()
    (legacy / "vscode" / "settings.json").write_text("{}")

    migrate_manager.backup_manager.backup_dir = backup_dir
    success, new_path = migrate_manager.migrate_backup(legacy)
    assert success
    assert new_path is not None
    assert new_path.exists()
    assert (new_path / "cursor" / "test.txt").read_text() == "test"
    assert (new_path / "vscode" / "settings.json").read_text() == "{}"
    assert legacy.with_suffix(".legacy").exists()


def test_migrate_command(temp_dir: Path, test_config: Config) -> None:
    """Test migrate command."""
    # Create legacy backup structure
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir(parents=True)

    # Legacy backup 1
    legacy1 = backup_dir / "testrepo1"
    legacy1.mkdir()
    (legacy1 / "cursor").mkdir()
    (legacy1 / "cursor" / "test1.txt").write_text("test1")

    # Legacy backup 2
    legacy2 = backup_dir / "testrepo2"
    legacy2.mkdir()
    (legacy2 / "cursor").mkdir()
    (legacy2 / "cursor" / "test2.txt").write_text("test2")

    args = argparse.Namespace(
        repo=None,
        branch="main",
        dry_run=False,
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert migrate(args, test_config) == 0

    # Check that backups were migrated
    assert legacy1.with_suffix(".legacy").exists()
    assert legacy2.with_suffix(".legacy").exists()
    assert not legacy1.exists()
    assert not legacy2.exists()

    # Check new backup structure
    new_backup1 = list((backup_dir / "testrepo1" / "main").iterdir())[0]
    new_backup2 = list((backup_dir / "testrepo2" / "main").iterdir())[0]
    assert (new_backup1 / "cursor" / "test1.txt").read_text() == "test1"
    assert (new_backup2 / "cursor" / "test2.txt").read_text() == "test2"


def test_migrate_specific_repo(temp_dir: Path, test_config: Config) -> None:
    """Test migrating a specific repository."""
    # Create legacy backup structure
    backup_dir = temp_dir / "backups"
    backup_dir.mkdir(parents=True)

    # Legacy backup 1
    legacy1 = backup_dir / "testrepo1"
    legacy1.mkdir()
    (legacy1 / "cursor").mkdir()
    (legacy1 / "cursor" / "test1.txt").write_text("test1")

    # Legacy backup 2
    legacy2 = backup_dir / "testrepo2"
    legacy2.mkdir()
    (legacy2 / "cursor").mkdir()
    (legacy2 / "cursor" / "test2.txt").write_text("test2")

    args = argparse.Namespace(
        repo="testrepo1",
        branch="main",
        dry_run=False,
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(temp_dir)
        assert migrate(args, test_config) == 0

    # Check that only testrepo1 was migrated
    assert legacy1.with_suffix(".legacy").exists()
    assert not legacy2.with_suffix(".legacy").exists()
    assert not legacy1.exists()
    assert legacy2.exists()

    # Check new backup structure
    new_backup1 = list((backup_dir / "testrepo1" / "main").iterdir())[0]
    assert (new_backup1 / "cursor" / "test1.txt").read_text() == "test1"
