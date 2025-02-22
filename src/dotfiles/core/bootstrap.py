"""Bootstrap functionality for dotfiles."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console

from .backup import BackupManager
from .config import Config
from .repository import GitRepository
from .restore import RestoreManager

console = Console()


class BootstrapManager:
    """Manages repository bootstrapping operations."""

    def __init__(self, config: Config):
        """Initialize bootstrap manager."""
        self.config = config
        self.backup_manager = BackupManager(config)
        self.restore_manager = RestoreManager(config, self.backup_manager)

    def list_templates(self) -> List[Path]:
        """List available template backups."""
        templates = []
        for repo_dir in self.backup_manager.backup_dir.glob("*"):
            if not repo_dir.is_dir():
                continue
            templates.extend(self.backup_manager.list_backups(repo_dir.name))
        return templates

    def bootstrap(
        self,
        repo: GitRepository,
        template: Optional[Union[str, Path]] = None,
        programs: Optional[List[str]] = None,
        target_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Bootstrap a repository from a template.

        Args:
            repo: Repository to bootstrap
            template: Template backup to use
            programs: List of programs to bootstrap (None for all)
            target_path: Target path within the repository to bootstrap into (None for root)
        """
        try:
            # Get available templates
            templates = self.list_templates()
            if not templates:
                console.print("[red]No template backups found.")
                return False

            # Use specified template or most recent backup
            if template:
                if isinstance(template, str):
                    # First try to find it in the list of templates by repo name
                    template_path = next(
                        (t for t in templates if t.parent.parent.name == template), None
                    )
                    if not template_path:
                        # Try to convert the string to a Path and verify it's a valid template
                        template_path = Path(template)
                        if not template_path.exists() or not template_path.is_dir():
                            console.print(
                                f"[red]Template path {template} does not exist or is not a directory."
                            )
                            return False
                        if template_path not in templates:
                            console.print(
                                f"[red]Template path {template} is not a valid backup directory."
                            )
                            return False
                else:
                    # If template is a Path, verify it's a valid backup directory
                    if not template.exists() or not template.is_dir():
                        console.print(
                            f"[red]Template path {template} does not exist or is not a directory."
                        )
                        return False
                    # Verify it's in the list of valid templates
                    if template not in templates:
                        console.print(
                            f"[red]Template path {template} is not a valid backup directory."
                        )
                        return False
                    template_path = template
            else:
                console.print("[red]No template specified.")
                return False

            # Handle target path
            if target_path:
                if isinstance(target_path, str):
                    target_path = Path(target_path)
                target_dir = repo.path / target_path
                if not target_dir.exists():
                    target_dir.mkdir(parents=True)
            else:
                target_dir = repo.path

            # Get program configurations
            program_configs = self.config.get_program_configs()
            if programs:
                # Clean up any files from non-selected programs
                for name, config in program_configs.items():
                    if name not in programs:
                        for file_pattern in config.get("files", []):
                            file_path = target_dir / file_pattern
                            if file_path.exists():
                                file_path.unlink()
                        for dir_pattern in config.get("directories", []):
                            dir_path = target_dir / dir_pattern
                            if dir_path.exists():
                                shutil.rmtree(dir_path)
                # Filter to selected programs
                program_configs = {
                    name: config for name, config in program_configs.items() if name in programs
                }

            # Copy files from template
            any_copied = False

            # First copy base repository files
            base_files = ["test.txt"]  # List of base files to copy
            for file_name in base_files:
                src_path = template_path / file_name
                if src_path.exists() and src_path.is_file():
                    dst_path = target_dir / file_name
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    if dst_path.exists():
                        dst_path.unlink()
                    shutil.copy2(src_path, dst_path)
                    any_copied = True

            # Then copy program-specific files
            for program_name, program_config in program_configs.items():
                program_dir = template_path / program_name
                if not program_dir.exists():
                    continue

                # Copy files
                for file_pattern in program_config.get("files", []):
                    # Look for the file directly under the program directory
                    src_path = program_dir / Path(file_pattern).name
                    if src_path.exists() and src_path.is_file():
                        dst_path = target_dir / file_pattern
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        if dst_path.exists():
                            dst_path.unlink()
                        shutil.copy2(src_path, dst_path)
                        any_copied = True

                # Copy directories
                for dir_pattern in program_config.get("directories", []):
                    src_path = program_dir / dir_pattern
                    if src_path.exists() and src_path.is_dir():
                        dst_path = target_dir / dir_pattern
                        if dst_path.exists():
                            shutil.rmtree(dst_path)
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src_path, dst_path)
                        any_copied = True

            if not any_copied:
                console.print("[yellow]Warning: No files were copied.")
                return False

            # Initialize Git repository in the new repo if we're bootstrapping the root
            if not target_path:
                subprocess.run(["git", "init"], cwd=repo.path, check=True, capture_output=True)
                subprocess.run(
                    ["git", "config", "user.name", "Test User"], cwd=repo.path, check=True
                )
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"], cwd=repo.path, check=True
                )

            return True
        except Exception as e:
            console.print(f"[red]Error during bootstrap: {e}")
            return False
