# Development Dotfiles Manager

A specialized dotfiles management system for maintaining consistent configurations across multiple development repositories. This tool helps you keep your development environment consistent by easily backing up and restoring configuration files between different project repositories.

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

# Backup your configurations
dotfiles backup ~/projects/myrepo

# List available backups
dotfiles list

# Restore configurations (automatically uses the latest backup)
dotfiles restore /path/to/target/directory
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

# Backup configurations
dotfiles backup REPO_PATH [--programs] [--branch BRANCH] [--dry-run]

# Restore configurations
dotfiles restore TARGET_DIR [BACKUP_DIR] [--force] [--dry-run]

# Wipe configurations
dotfiles wipe REPO_PATH [--programs] [--force] [--dry-run]
```

### Backup Operations

```bash
# Backup all configurations from a repository
dotfiles backup ~/projects/myrepo

# List available programs instead of backing up
dotfiles backup ~/projects/myrepo --programs

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

- **Automatic Backup Selection**: When restoring, the tool automatically finds and uses the latest backup if no specific backup is provided.
- **Backup Validation**: After restoring files, the tool validates that all files were restored correctly.
- **Branch-Specific Backups**: Create and restore backups for specific Git branches.
- **Dry Run Mode**: Preview what would be backed up or restored without making any changes.
- **Detailed Reporting**: Get comprehensive information about your backups and restore operations.
- **Force Mode**: Overwrite existing files when restoring.

## Detailed Command Reference

### Restore Command

The restore command allows you to restore configurations from backups to a target directory:

```bash
dotfiles restore [REPO_NAME] [TARGET_DIR] [--date DATE] [--branch BRANCH] [--latest] [--force] [--dry-run]
```

**Arguments:**
- `REPO_NAME` (optional): The name of the repository to restore from. If not specified, will try to determine it from the target directory or current directory.
- `TARGET_DIR` (optional): The directory to restore configurations to. If not specified, will use the current directory.

**Options:**
- `--date`: Date to restore from (format: YYYYMMDD or YYYYMMDD-HHMMSS).
- `--branch`: Branch to restore from.
- `--latest`: Use the latest backup regardless of date.
- `--force`: Force restore over existing files.
- `--dry-run`: Show what would be restored without making any changes.

**Examples:**

1. Restore latest backup for the current directory:
   ```bash
   dotfiles restore
   ```

2. Restore from a specific repository to current directory:
   ```bash
   dotfiles restore cursor-tools
   ```

3. Restore from a specific repository to a different directory:
   ```bash
   dotfiles restore cursor-tools /tmp/test-restore
   ```

4. Restore from "main" branch:
   ```bash
   dotfiles restore cursor-tools --branch main
   ```

5. Restore from a specific date:
   ```bash
   dotfiles restore cursor-tools --date 20250226
   ```

6. Restore latest backup, ignoring date and branch parameters if any:
   ```bash
   dotfiles restore cursor-tools --latest
   ```

After restoring, the tool will validate that all files were restored correctly and display a summary of the operation.

## Supported Configurations

- **Cursor Development**
  - `.cursorrules` - Cursor IDE configuration rules
  - `.cursorsettings` - Cursor IDE settings
  - `.cursor/` directory - Additional Cursor configurations and cache

- **Windsurf Development**
  - `.windsurfrules` - Windsurf development rules and configurations

- **VSCode Integration**
  - `.vscode/` directory - Editor settings and extensions

- **Git Configuration**
  - `.gitignore` - Repository ignore patterns
  - `.gitmessage` - Commit message templates
  - `.gitattributes` - Repository attributes

## Configuration

### Global Configuration
Create or edit `~/.dotfilesrc`:
```yaml
search_paths:
  - ~/projects
  - ~/source
max_depth: 3
exclude_patterns:
  - node_modules
  - .venv
```

### Local Configuration
Create or edit `.dotfilesrc` in your repository:
```yaml
programs:
  cursor:
    files:
      - .cursorrules
      - .cursorsettings
    directories:
      - .cursor
```
