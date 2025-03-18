# Cursor Dotfiles Management Tool

## Purpose and Summary

The `dotfiles` repository provides a specialized command-line tool for managing Cursor IDE configuration files across multiple repositories. It focuses exclusively on backing up, restoring, listing, and managing `.cursor` directory contents and related configuration files, ensuring consistency in your Cursor development environment. The project is built using Python and utilizes libraries such as `click` for the CLI, `rich` for enhanced output and progress indicators, `PyYAML` for configuration management, and `GitPython` for interaction with Git repositories.

## Quick Start

This section provides a quick introduction to installing and using the core features of the `dotfiles` tool.

### Installation
Although the repository uses uv the tool is currently designed to be used globally installed, so that it is available everywhere on your system and not only inside one project.

```bash
# Clone the repository
git clone https://github.com/yourusername/dotfiles.git
cd dotfiles

# Install the package using pip (consider using uv for other tasks like testing)
pip install .
# or for development:
pip install -e ".[dev]"

```

### Basic Usage

List available backups:
```bash
dotfiles list
```

Backup configurations from a repository:
```bash
dotfiles backup ~/path/to/your/repo
```

Restore configurations to a repository (automatically uses latest backup):
```bash
dotfiles restore /path/to/target/repo
```

## Configuration Options

The `dotfiles` tool uses a simplified YAML configuration, typically located at `~/.dotfilesrc`. The configuration now focuses exclusively on Cursor-related settings with reasonable defaults.

Example of a custom `~/.dotfilesrc`:
```yaml
search_paths:
  - ~/projects
  - ~/source
max_depth: 3
exclude_patterns:
  - node_modules
  - .venv
```
- `search_paths`: List of directories to search for repositories
- `max_depth`: Maximum depth to search for repositories within search paths
- `exclude_patterns`: List of patterns to exclude when searching for repositories

The tool automatically handles Cursor configuration files without requiring explicit configuration.

## Package: `dotfiles`

### Summary

The `dotfiles` package offers a streamlined command-line interface (CLI) tool for managing Cursor IDE configurations. The CLI uses the `click` library, providing commands such as `backup`, `restore`, `list`, and `wipe`. The core logic is organized into modules within the `dotfiles.core` package, with enhanced features like progress indicators, structured logging, and zip file export capabilities.

### Installation

The `dotfiles` package is designed to be installed globally using pip.

```bash
pip install /path/to/dotfiles/repo
```

### Public Interface Documentation

#### `dotfiles.cli` Module (`src/dotfiles/cli.py`)

##### `cli()`

* **Purpose**: Main entry point group for the Cursor dotfiles command-line interface
* **Usage**: `dotfiles [COMMAND] --help`
* **Description**: The root command group for all Cursor configuration management commands

##### `backup(repo_path: Path, branch: Optional[str], dry_run: bool, zip_export: bool)`

* **Purpose**: Backs up Cursor configurations from a specified repository

* **Parameters**:
    * `repo_path` (Path): Path to the repository to be backed up
    * `branch` (Optional[str]): The branch to back up (defaults to the current branch)
    * `dry_run` (bool): If True, simulates the backup process without making changes
    * `zip_export` (bool): If True, creates a zip archive of the backup

* **Usage**:
    ```bash
    dotfiles backup ~/source/myrepo
    dotfiles backup ~/source/myrepo --branch feature-branch
    dotfiles backup ~/source/myrepo --dry-run
    dotfiles backup ~/source/myrepo --zip-export
    ```

##### `restore(repo_name: str, target_dir: Path, branch: Optional[str], date: Optional[str], latest: bool, force: bool, dry_run: bool)`

* **Purpose**: Restores Cursor configurations from a backup to a target directory
* **Parameters**:
    * `repo_name`: Name of repository to restore from
    * `target_dir`: Path to directory to restore to
    * `branch` (Optional[str]): Branch to restore from
    * `date` (Optional[str]): Date of the backup to restore (format: YYYYMMDD-HHMMSS or YYYYMMDD)
    * `latest` (bool): If True, restores the latest backup
    * `force` (bool): If True, overwrites existing files
    * `dry_run` (bool): If True, simulates the restore process without making changes

* **Usage**:
    ```bash
    dotfiles restore myrepo ~/source/project
    dotfiles restore myrepo ~/source/project --branch main --date 20250226-184209
    dotfiles restore myrepo ~/source/project --force
    dotfiles restore myrepo ~/source/project --dry-run
    ```

##### `list(repo: Optional[str], verbose: bool = False, latest: bool = False)`

*   **Purpose**: Lists available backups.

*   **Parameters**:
    *   `repo` (Optional[str]): Repository name to filter backups.
    *   `verbose` (bool): If True, shows detailed backup information.
    *   `latest` (bool): If True, shows only the latest backup for each repository and branch.

*   **Usage**:

     ```bash
   dotfiles list
   dotfiles list harmonyhub
   dotfiles list --verbose
   dotfiles list --latest
   dotfiles list harmonyhub --latest --verbose
     ```

##### `wipe(repo_name: str, branch: Optional[str], date: Optional[str], force: bool)`

*   **Purpose**: Deletes backups for a repository.

*   **Parameters**:
    *   `repo_name` (str): Name of the repository to wipe backups for.
    *   `branch` (Optional[str]): Branch to wipe.
    *   `date` (Optional[str]): Date of the backup to wipe.
    *   `force` (bool): If True, skips confirmation prompt.

*   **Usage**:
     ```bash
      dotfiles wipe harmonyhub
      dotfiles wipe harmonyhub --branch main
      dotfiles wipe harmonyhub --date 20250226-184209
      dotfiles wipe harmonyhub --force
     ```

##### `init()`

*   **Purpose**: Initializes the dotfiles configuration. (Currently not fully implemented).
* **Usage**: `dotfiles init`

##### `main()`
* **Purpose**: CLI Entry Point
* **Description**: This function calls the `cli()` and is the entry point for the package.

#### `dotfiles.core.config` Module (`src/dotfiles/core/config.py`)

##### `Config` Class

*   **Purpose**:  Manages the dotfiles configuration.
*   **Attributes**:
    *   `search_paths` (List[str]):  List of paths to search for repositories.
    *   `max_depth` (int): Maximum directory depth to search for repositories.
    *   `exclude_patterns` (List[str]):  List of file/directory patterns to exclude.
    *   `programs` (Dict[str, Dict[str, Any]]):  Configuration for each program.
*   **Methods**:
    *   `load_config(config_path: Path)`: Loads configuration from a YAML file.
    *   `_merge_config(config: Dict[str, Any])`: Merges a given configuration dictionary with the current configuration.
    *   `validate() -> List[str]`: Validates the current configuration and returns a list of errors.
    *   `get_program_configs() -> Dict[str, Dict[str, Any]]`: Returns all program configurations.
    *   `get_program_config(program: str) -> Optional[Dict[str, Any]]`: Returns the configuration for a specific program.

#### `dotfiles.core.backup` Module (`src/dotfiles/core/backup.py`)

##### `BackupManager` Class

* **Purpose**: Manages backup operations for Cursor configurations
* **Attributes**:
    * `config` (Config): The loaded dotfiles configuration
    * `console` (Console): A Rich Console instance for output and progress
    * `backup_dir` (Path): The directory where backups are stored
    * `logger` (Logger): Structured logger for operation tracking
* **Methods**:
    * `backup_path(repo: GitRepository) -> Path`: Generates a backup path for the given repository
    * `get_cursor_paths(repo: GitRepository) -> Set[Path]`: Gets all Cursor configuration paths to be backed up
    * `backup(repo: GitRepository | Path, branch: Optional[str] = None, dry_run: bool = False, zip_export: bool = False) -> bool`: Performs the backup operation with optional zip export
    * `create_zip_backup(backup_path: Path, output_path: Optional[Path] = None) -> Path`: Creates a zip archive of a backup
    * `list_backups(repo: Optional[str] = None) -> List[Path]`: Lists available backups

#### `dotfiles.core.restore` Module (`src/dotfiles/core/restore.py`)

##### `RestoreManager` Class

*   **Purpose**: Manages restoring program configurations from backups.
*   **Attributes**:
    *   `config` (Config): The loaded dotfiles configuration.
    *   `backup_manager` (BackupManager): An instance of BackupManager.
    *   `console` (Console):  A Rich Console instance for output.
    *    `backup_dir` (Path):  The directory where backups are stored.
*   **Methods**:
    *   `find_backup(repo_name: str, branch: Optional[str] = None, date: Optional[str] = None, latest: bool = False) -> Optional[Path]`: Locates a specific backup based on criteria.
    *   `get_program_paths(repo: GitRepository, program: str) -> Set[Path]`: Gets all paths to restore for a specified program.
    *  `check_conflicts(repo: GitRepository, backup_path: Path) -> Set[Tuple[Path, Path]]`: Checks for file conflicts between the target directory and the backup, before restoring.
    *   `restore_program(program: str, source_dir: Path, target_dir: Path, force: bool = False, dry_run: bool = False) -> bool`: Restores a single program's configurations.
    *   `validate_restore(backup_path: Path, target_dir: Path, programs: List[str]) -> Tuple[bool, Dict[str, Dict[str, List[Tuple[Path, Optional[str]]]]]]`:  Validates that files were restored correctly.
    *   `display_validation_results(validation_results: Dict[str, Dict[str, List[Tuple[Path, Optional[str]]]]])`: Displays validation results in a user-friendly format.
    *   `restore(repo_name: str, target_dir: Path, programs: Optional[List[str]] = None, branch: Optional[str] = None, date: Optional[str] = None, latest: bool = False, force: bool = False, dry_run: bool = False) -> bool`: Performs the restore operation, finding the appropriate backup and restoring specified programs.

#### `dotfiles.core.repository` Module (`src/dotfiles/core/repository.py`)

##### `GitRepository` Class

*   **Purpose**: Represents and interacts with a Git repository.
*   **Attributes**:
    *   `path` (Path):  The path to the repository.
    *   `name` (str):  The name of the repository (derived from the path).
*   **Methods**:
    *   `exists() -> bool`:  Checks if the repository exists and is a valid Git repository.
    *   `_run_git(*args: str) -> str`:  Runs a Git command in the repository and returns the output.
    *   `init()`: Initializes a new Git repository.


--- End of Documentation ---
