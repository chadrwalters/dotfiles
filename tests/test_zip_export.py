"""Tests for the zip export functionality."""

import os
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from rich.progress import Progress

from dotfiles.core.zip_export import ZipExporter


def test_zip_export_creates_valid_archive(tmp_path: Path) -> None:
    """Test that ZipExporter creates a valid zip archive with correct structure."""
    # Create test files
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    test_file = source_dir / "test.txt"
    test_file.write_text("test content")

    subdir = source_dir / "subdir"
    subdir.mkdir()
    subdir_file = subdir / "subfile.txt"
    subdir_file.write_text("subdir content")

    # Create zip archive
    output_path = tmp_path / "output.zip"
    exporter = ZipExporter(str(source_dir), str(output_path))
    exporter.export()

    # Verify zip was created
    assert output_path.exists()

    # Verify zip contents
    with zipfile.ZipFile(output_path) as zf:
        # Check file list
        file_list = zf.namelist()
        assert "test.txt" in file_list
        assert os.path.join("subdir", "subfile.txt") in file_list

        # Check file contents
        assert zf.read("test.txt").decode() == "test content"
        assert zf.read(os.path.join("subdir", "subfile.txt")).decode() == "subdir content"


def test_zip_export_with_progress(tmp_path: Path) -> None:
    """Test that ZipExporter works with progress tracking."""
    # Create test file
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    test_file = source_dir / "test.txt"
    test_file.write_text("test content")

    # Create zip with progress
    output_path = tmp_path / "output.zip"
    exporter = ZipExporter(str(source_dir), str(output_path))

    with Progress() as progress:
        exporter.export(progress)

    assert output_path.exists()


def test_zip_export_handles_missing_source() -> None:
    """Test that ZipExporter properly handles missing source directory."""
    with TemporaryDirectory() as tmpdir:
        source_dir = Path(tmpdir) / "nonexistent"
        output_path = Path(tmpdir) / "output.zip"

        exporter = ZipExporter(str(source_dir), str(output_path))

        with pytest.raises(ValueError, match="Source directory .* does not exist"):
            exporter.export()


def test_zip_export_creates_output_dirs(tmp_path: Path) -> None:
    """Test that ZipExporter creates output directories if they don't exist."""
    # Create source
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    test_file = source_dir / "test.txt"
    test_file.write_text("test content")

    # Create zip in nested directory
    output_path = tmp_path / "nested" / "dirs" / "output.zip"
    exporter = ZipExporter(str(source_dir), str(output_path))
    exporter.export()

    assert output_path.exists()
