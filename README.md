# Cursor Development Dotfiles Manager

A specialized dotfiles management system focused exclusively on managing Cursor IDE configurations. This tool helps you maintain consistent Cursor development environments by easily backing up and restoring your `.cursor` directory and related configuration files across different projects.

## Quick Start

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/dotfiles.git
cd dotfiles

# Create and activate virtual environment with UV
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
uv pip install -e ".[dev]"

# Run the dotfiles command
dotfiles --help

# Backup your Cursor configurations
dotfiles backup ~/projects/myrepo

# List available backups
dotfiles list

# Restore Cursor configurations
dotfiles restore /path/to/target/directory

# Export configurations to a zip file (new feature)
dotfiles backup ~/projects/myrepo --zip-export
```

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Git
- UV package manager

### Setting Up Development Environment

1. **Install UV**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create Virtual Environment**
   ```bash
   uv venv
   source .venv/bin/activate  # Unix/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   # Install all dependencies including development tools
   uv pip install -e ".[dev]"
   ```

4. **Verify Installation**
   ```bash
   # Run tests
   pytest

   # Check code formatting
   black --check .
   isort --check .
   ruff check .
   mypy .
   ```

## Usage

### Basic Commands

```bash
# List available backups
dotfiles list [REPO] [--verbose] [--latest]

# Backup Cursor configurations
dotfiles backup REPO_PATH [--branch BRANCH] [--dry-run]

# Restore Cursor configurations
dotfiles restore TARGET_DIR [BACKUP_DIR] [--force] [--dry-run]

# Wipe Cursor configurations
dotfiles wipe REPO_PATH [--force] [--dry-run]
```

### Backup Operations

```bash
# Backup Cursor configurations from a repository
dotfiles backup ~/projects/myrepo

# Backup from a specific branch
dotfiles backup ~/projects/myrepo --branch feature-branch

# Perform a dry run (show what would be backed up without doing it)
dotfiles backup ~/projects/myrepo --dry-run
```

### Restore Operations

```bash
# Restore to a target directory using the latest backup (automatically detected)
dotfiles restore /path/to/target/directory

# Restore from a specific repository to a target directory
dotfiles restore repo-name /path/to/target/directory

# Restore from a specific branch
dotfiles restore repo-name /path/to/target/directory --branch main

# Restore from a specific date
dotfiles restore repo-name /path/to/target/directory --date 20250226

# Force restore over existing files
dotfiles restore repo-name /path/to/target/directory --force

# Perform a dry run (show what would be restored without doing it)
dotfiles restore repo-name /path/to/target/directory --dry-run
```

### List Operations

```bash
# List all available backups
dotfiles list

# List backups for a specific repository
dotfiles list myrepo

# Show detailed information about backups
dotfiles list --verbose

# Show only the latest backup for each repository
dotfiles list --latest
```

## Features

- **Cursor-Focused Management**: Specialized handling of `.cursor` directory and related configuration files
- **Automatic Backup Selection**: When restoring, the tool automatically finds and uses the latest backup
- **Backup Validation**: Validates that all Cursor configuration files are restored correctly
- **Branch-Specific Backups**: Create and restore backups for specific Git branches
- **Dry Run Mode**: Preview operations without making changes
- **Detailed Progress**: Real-time progress indicators for all operations
- **Zip Export**: Export configurations as a zip file for easy sharing (coming soon)
- **Structured Logging**: Comprehensive logging with rotation for better debugging

## Supported Configurations

The tool now exclusively manages Cursor IDE configurations:

- `.cursor/` directory - Contains all Cursor-specific configurations including:
  - Rules
  - Settings
  - Cache
  - Workspace state
  - Extensions configuration

## Configuration

The configuration has been simplified to focus on Cursor files. Create or edit `~/.dotfilesrc`:

```yaml
# Global Configuration
search_paths:
  - ~/projects
  - ~/source
max_depth: 3
exclude_patterns:
  - node_modules
  - .venv
```

Local configuration (`.dotfilesrc` in your repository) is optional and will be automatically configured for Cursor files.

## Migration Guide

Version 2.0 focuses exclusively on Cursor IDE configurations. If you're upgrading from a previous version:

1. **Configuration Updates**
   - Previous versions managed multiple program configurations
   - Now focuses solely on `.cursor` directory and related files
   - Your existing `.dotfilesrc` will be automatically migrated
   - Non-Cursor configurations will be ignored

2. **Backup Changes**
   - Previous backups remain compatible
   - New backups will only include Cursor-related files
   - Use `--zip-export` flag to create shareable backups

3. **Command Changes**
   - All commands now operate only on Cursor files
   - Added progress indicators for better visibility
   - Enhanced logging for troubleshooting

4. **Automatic Migration**
   The tool will automatically:
   - Detect and migrate old configuration formats
   - Preserve existing backups
   - Update to the new cursor-focused structure

For detailed migration assistance, run:
```bash
dotfiles doctor --migration-check
```
