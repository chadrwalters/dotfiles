"""
Module for handling zip file exports of dotfiles.

This module provides functionality to export dotfiles into a zip archive
while maintaining the original directory structure.
"""

import os
import zipfile
from pathlib import Path
from typing import List, Optional

from rich.progress import Progress, TaskID


class ZipExporter:
    """Handles the export of dotfiles to a zip archive."""

    def __init__(self, source_dir: str, output_path: str):
        """
        Initialize the ZipExporter.

        Args:
            source_dir: Directory containing files to export
            output_path: Path where the zip file should be created
        """
        self.source_dir = Path(source_dir)
        self.output_path = Path(output_path)

    def export(self, progress: Optional[Progress] = None) -> None:
        """
        Export files to a zip archive.

        Args:
            progress: Optional Progress instance for progress tracking

        Raises:
            OSError: If there are file permission or disk space issues
            ValueError: If the source directory doesn't exist
        """
        if not self.source_dir.exists():
            raise ValueError(f"Source directory {self.source_dir} does not exist")

        # Create parent directories if they don't exist
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get list of files to zip
        files_to_zip = self._get_files_to_zip()

        # Create progress tracking if provided
        task_id: Optional[TaskID] = None
        if progress:
            task_id = progress.add_task(
                f"Creating zip archive: {self.output_path.name}", total=len(files_to_zip)
            )

        try:
            with zipfile.ZipFile(self.output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in files_to_zip:
                    rel_path = file_path.relative_to(self.source_dir)
                    zf.write(file_path, rel_path)

                    if progress and task_id is not None:
                        progress.advance(task_id)

        except OSError as e:
            # Handle common errors like disk full or permission issues
            if self.output_path.exists():
                self.output_path.unlink()
            raise OSError(f"Failed to create zip archive: {e}") from e

    def _get_files_to_zip(self) -> List[Path]:
        """
        Get list of files to include in the zip archive.

        Returns:
            List of Path objects for files to zip
        """
        files = []
        for root, _, filenames in os.walk(self.source_dir):
            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                files.append(file_path)
        return files
