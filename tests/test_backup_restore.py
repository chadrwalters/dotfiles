"""Tests for backup and restore functionality."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from src.dotfiles.core.backup import BackupManager
from src.dotfiles.core.config import Config
from src.dotfiles.core.repository import GitRepository
from src.dotfiles.core.restore import RestoreManager


class TestBackupRestore(TestCase):
    """Test backup and restore functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories
        self.test_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.test_dir / "source"
        self.target_dir = self.test_dir / "target"
        self.backup_dir = self.test_dir / "backups"

        # Create source directory structure
        self.source_dir.mkdir()
        self.target_dir.mkdir()
        self.backup_dir.mkdir()

        # Initialize git repository in source directory
        os.chdir(self.source_dir)
        os.system("git init")

        # Create test files and directories
        self._create_test_files()

        # Create config
        self.config = Config()

        # Override backup directory
        self.backup_manager = BackupManager(self.config)
        self.backup_manager.backup_dir = self.backup_dir

        # Create restore manager
        self.restore_manager = RestoreManager(self.config, self.backup_manager)
        self.restore_manager.backup_dir = self.backup_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create test files and directories."""
        # Create cursor files
        cursor_dir = self.source_dir / ".cursor"
        cursor_dir.mkdir()
        cursor_rules_dir = cursor_dir / "rules"
        cursor_rules_dir.mkdir()

        # Create cursor rules file
        cursor_rules_file = self.source_dir / ".cursorrules"
        cursor_rules_file.write_text("# Cursor rules")

        # Create cursor rule file
        cursor_rule_file = cursor_rules_dir / "test.mdc"
        cursor_rule_file.write_text("# Cursor rule file")

        # Create vscode directory
        vscode_dir = self.source_dir / ".vscode"
        vscode_dir.mkdir()

        # Create vscode settings file
        vscode_settings_file = vscode_dir / "settings.json"
        vscode_settings_file.write_text('{"settings": "test"}')

    def test_backup(self):
        """Test backup functionality."""
        # Create repository
        repo = GitRepository(self.source_dir)

        # Backup
        result = self.backup_manager.backup(repo)
        self.assertTrue(result)

        # Check if backup directory exists
        repo_backup_dir = self.backup_dir / repo.name / repo.get_current_branch()
        self.assertTrue(repo_backup_dir.exists())

        # Get latest backup
        backups = list(repo_backup_dir.iterdir())
        self.assertTrue(len(backups) > 0)
        latest_backup = max(backups, key=lambda p: p.name)

        # Check if cursor directory exists in backup
        cursor_backup_dir = latest_backup / "cursor"
        self.assertTrue(cursor_backup_dir.exists())

        # Check if cursor files were backed up
        self.assertTrue((cursor_backup_dir / ".cursorrules").exists())
        self.assertTrue((cursor_backup_dir / ".cursor").exists())
        self.assertTrue((cursor_backup_dir / ".cursor" / "rules").exists())
        self.assertTrue((cursor_backup_dir / ".cursor" / "rules" / "test.mdc").exists())

        # Check if vscode directory exists in backup
        vscode_backup_dir = latest_backup / "vscode"
        self.assertTrue(vscode_backup_dir.exists())

        # Check if vscode files were backed up
        self.assertTrue((vscode_backup_dir / ".vscode").exists())
        self.assertTrue((vscode_backup_dir / ".vscode" / "settings.json").exists())

        return latest_backup

    def test_restore(self):
        """Test restore functionality."""
        # First backup
        latest_backup = self.test_backup()

        # Create repository
        repo = GitRepository(self.target_dir)

        # Restore
        result = self.restore_manager.restore_program("cursor", latest_backup, self.target_dir)
        self.assertTrue(result)
        result = self.restore_manager.restore_program("vscode", latest_backup, self.target_dir)
        self.assertTrue(result)

        # Check if files were restored
        self.assertTrue((self.target_dir / ".cursorrules").exists())
        self.assertTrue((self.target_dir / ".cursor").exists())
        self.assertTrue((self.target_dir / ".cursor" / "rules").exists())
        self.assertTrue((self.target_dir / ".cursor" / "rules" / "test.mdc").exists())
        self.assertTrue((self.target_dir / ".vscode").exists())
        self.assertTrue((self.target_dir / ".vscode" / "settings.json").exists())

        # Check file contents
        self.assertEqual((self.target_dir / ".cursorrules").read_text(), "# Cursor rules")
        self.assertEqual(
            (self.target_dir / ".cursor" / "rules" / "test.mdc").read_text(), "# Cursor rule file"
        )
        self.assertEqual(
            (self.target_dir / ".vscode" / "settings.json").read_text(), '{"settings": "test"}'
        )

        # Validate restore
        is_valid, validation_results = self.restore_manager.validate_restore(
            latest_backup, self.target_dir, ["cursor", "vscode"]
        )
        self.assertTrue(is_valid)
        self.assertTrue("cursor" in validation_results)
        self.assertTrue("vscode" in validation_results)
        self.assertTrue(len(validation_results["cursor"]["success"]) > 0)
        self.assertTrue(len(validation_results["vscode"]["success"]) > 0)
        self.assertEqual(len(validation_results["cursor"]["failed"]), 0)
        self.assertEqual(len(validation_results["vscode"]["failed"]), 0)

    def test_restore_with_modifications(self):
        """Test restore validation with modified files."""
        # First backup
        latest_backup = self.test_backup()

        # Create repository
        repo = GitRepository(self.target_dir)

        # Restore
        result = self.restore_manager.restore_program("cursor", latest_backup, self.target_dir)
        self.assertTrue(result)
        result = self.restore_manager.restore_program("vscode", latest_backup, self.target_dir)
        self.assertTrue(result)

        # Modify a file
        (self.target_dir / ".cursorrules").write_text("# Modified cursor rules")

        # Validate restore
        is_valid, validation_results = self.restore_manager.validate_restore(
            latest_backup, self.target_dir, ["cursor", "vscode"]
        )
        self.assertFalse(is_valid)
        self.assertTrue("cursor" in validation_results)
        self.assertTrue(len(validation_results["cursor"]["failed"]) > 0)

        # Check if the failure reason contains "Content mismatch"
        failed_path, reason = validation_results["cursor"]["failed"][0]
        self.assertEqual(failed_path, self.target_dir / ".cursorrules")
        self.assertTrue("Content mismatch" in reason)

    def test_restore_with_missing_files(self):
        """Test restore validation with missing files."""
        # First backup
        latest_backup = self.test_backup()

        # Create repository
        repo = GitRepository(self.target_dir)

        # Restore
        result = self.restore_manager.restore_program("cursor", latest_backup, self.target_dir)
        self.assertTrue(result)
        result = self.restore_manager.restore_program("vscode", latest_backup, self.target_dir)
        self.assertTrue(result)

        # Remove a file
        (self.target_dir / ".cursorrules").unlink()

        # Validate restore
        is_valid, validation_results = self.restore_manager.validate_restore(
            latest_backup, self.target_dir, ["cursor", "vscode"]
        )
        self.assertFalse(is_valid)
        self.assertTrue("cursor" in validation_results)
        self.assertTrue(len(validation_results["cursor"]["failed"]) > 0)

        # Check if the failure reason contains "does not exist"
        failed_path, reason = validation_results["cursor"]["failed"][0]
        self.assertEqual(failed_path, self.target_dir / ".cursorrules")
        self.assertTrue("does not exist" in reason)

    def test_force_restore(self):
        """Test force restore over existing files."""
        # First backup
        latest_backup = self.test_backup()

        # Create repository
        repo = GitRepository(self.target_dir)

        # Create existing files with different content
        cursor_rules_file = self.target_dir / ".cursorrules"
        cursor_rules_file.write_text("# Existing cursor rules")

        # Restore with force
        result = self.restore_manager.restore_program(
            "cursor", latest_backup, self.target_dir, force=True
        )
        self.assertTrue(result)

        # Check if files were restored with correct content
        self.assertEqual((self.target_dir / ".cursorrules").read_text(), "# Cursor rules")

        # Validate restore
        is_valid, validation_results = self.restore_manager.validate_restore(
            latest_backup, self.target_dir, ["cursor"]
        )
        self.assertTrue(is_valid)
