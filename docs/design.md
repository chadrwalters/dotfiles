# Technical Design Document: Enhanced Cursor-Tools Configuration Management

## Overview
This document outlines the technical design for a centralized CLI tool (`dotfiles`) that manages configuration files across repositories and branches, with special handling for Raycast extension compatibility.

## System Architecture

### Core Components

1. **Unified CLI Tool (`dotfiles.py`)**
   - Single entry point for all operations
   - Subcommand-based interface (backup, restore, bootstrap, wipe, list)
   - Branch-aware operations
   - Program-specific functionality
   - Configuration file support

### Repository Discovery

1. **Search Strategies**
   ```python
   def find_git_repositories(
       root_paths: List[Path],
       max_depth: int = 3,
       exclude_patterns: List[str] = None
   ) -> List[Path]
   ```
   - Configurable root search paths
   - Recursive search with depth limit
   - Pattern-based exclusions
   - Cache results for performance

2. **Configuration**
   ```yaml
   # ~/.dotfilesrc or ./.dotfilesrc
   search_paths:
     - ~/projects
     - ~/source
   max_depth: 3
   exclude_patterns:
     - node_modules
     - .venv
   ```

### Branch Management

1. **Branch Operations**
   ```python
   def switch_branch(repo_path: Path, branch_name: str, create: bool = False) -> bool:
       """
       Switch to specified branch, handling:
       - Uncommitted changes (stash)
       - Non-existent branches
       - Detached HEAD state
       """
       # Stash uncommitted changes
       stash_result = stash_changes(repo_path)

       try:
           # Try to switch branch
           switch_result = subprocess.run([
               'git', '-C', str(repo_path),
               'checkout', branch_name
           ], capture_output=True, text=True)

           if switch_result.returncode != 0 and create:
               # Create branch if requested
               create_result = subprocess.run([
                   'git', '-C', str(repo_path),
                   'checkout', '-b', branch_name
               ], capture_output=True, text=True)

           # Restore stashed changes if any
           if stash_result:
               restore_stash(repo_path)

           return True
       except subprocess.CalledProcessError as e:
           print(f"Error switching branch: {e.stderr}")
           if stash_result:
               restore_stash(repo_path)
           return False
   ```

2. **Stash Management**
   ```python
   def stash_changes(repo_path: Path) -> bool:
       """Stash uncommitted changes if any exist."""

   def restore_stash(repo_path: Path) -> bool:
       """Restore most recent stash."""
   ```

### Backup Structure

```python
# Enhanced backup structure with timestamps
backup_path = (
    BACKUP_DIR
    / repo_name
    / branch_name
    / datetime.now().strftime('%Y%m%d-%H%M%S')
    / program_name
)
```

### Configuration Management

1. **User Configuration**
   ```yaml
   # ~/.dotfilesrc
   programs:
     cursor:
       name: "Cursor"
       files: [".cursorrules", ".cursorsettings"]
       directories: [".cursor"]
     custom_program:
       name: "Custom Program"
       files: [".customrc"]
       directories: ["custom_dir"]
   ```

2. **Configuration Loading**
   ```python
   def load_config() -> Dict:
       """
       Load configuration from multiple sources:
       1. Default built-in config
       2. Global user config (~/.dotfilesrc)
       3. Local repo config (./.dotfilesrc)
       """
   ```

### Error Handling

1. **Git Operations**
   ```python
   class GitError(Exception):
       def __init__(self, message: str, command: str, output: str):
           self.message = message
           self.command = command
           self.output = output

   def run_git_command(
       repo_path: Path,
       command: List[str],
       error_message: str
   ) -> subprocess.CompletedProcess:
       """Run git command with proper error handling."""
       try:
           result = subprocess.run(
               ['git', '-C', str(repo_path)] + command,
               capture_output=True,
               text=True,
               check=True
           )
           return result
       except subprocess.CalledProcessError as e:
           raise GitError(
               message=error_message,
               command=' '.join(['git'] + command),
               output=f"stdout: {e.stdout}\nstderr: {e.stderr}"
           )
   ```

2. **User Feedback**
   ```python
   def show_progress(iterable, desc: str):
       """Show progress bar for operations."""
       return tqdm(iterable, desc=desc)
   ```

### Command Implementation

1. **Base Command**
   ```python
   class DotfilesCommand:
       """Base class for all commands."""
       def __init__(self, args: argparse.Namespace):
           self.args = args
           self.config = load_config()

       def run(self) -> int:
           """Execute the command."""
           raise NotImplementedError
   ```

2. **Dry Run Support**
   ```python
   class BackupCommand(DotfilesCommand):
       def run(self) -> int:
           if self.args.dry_run:
               return self.dry_run()
           return self.execute()

       def dry_run(self) -> int:
           """Show what would be done without doing it."""
   ```

## Testing Strategy

### Unit Tests
```python
class TestBranchOperations(unittest.TestCase):
    def setUp(self):
        # Set up test repository
        self.test_repo = Path('test_repo')
        subprocess.run(['git', 'init', str(self.test_repo)])

    def test_switch_branch_with_uncommitted_changes(self):
        # Create uncommitted changes
        (self.test_repo / 'test.txt').write_text('test')
        subprocess.run(['git', 'add', '.'], cwd=self.test_repo)

        # Try to switch branch
        result = switch_branch(self.test_repo, 'new-branch')
        self.assertTrue(result)

        # Verify changes are preserved
        self.assertTrue((self.test_repo / 'test.txt').exists())
```

### Integration Tests
```python
class TestBackupRestore(unittest.TestCase):
    def test_backup_restore_workflow(self):
        # Set up test repositories
        source_repo = create_test_repo('source')
        target_repo = create_test_repo('target')

        # Add test configurations
        add_test_configs(source_repo)

        # Backup
        backup_cmd = BackupCommand(args)
        self.assertEqual(backup_cmd.run(), 0)

        # Verify backup
        self.assertTrue(backup_exists(source_repo))

        # Restore
        restore_cmd = RestoreCommand(args)
        self.assertEqual(restore_cmd.run(), 0)

        # Verify restored files
        self.assertTrue(configs_match(source_repo, target_repo))
```

## Dependencies

- Python 3.8+
- UV for dependency and virtual environment management
- Git command-line tools
- Core dependencies (managed by UV):
  - PyYAML (for configuration files)
  - tqdm (for progress bars)
  - rich (for terminal UI)
- Development dependencies (managed by UV):
  - pytest (testing)
  - black, isort, ruff (code formatting and linting)
  - mypy (type checking)

## Legacy Compatibility

### Backup Structure Preservation
The system maintains compatibility with the existing backup structure:
```
backups/
└── repo_name/          # One backup per repo
    ├── cursor/         # Cursor configs
    ├── windsurf/       # Windsurf configs
    ├── vscode/         # VSCode settings
    └── git/            # Git configs
```

### Migration Strategy
1. **Backup Preservation**
   - Existing backups remain in their current structure
   - New backups follow the same organization pattern
   - Support reading from and writing to legacy backup format

2. **Command Compatibility**
   - New unified CLI maintains feature parity with legacy scripts
   - Support for all existing configuration types
   - Backward compatible configuration handling

## Future Enhancements

1. **User Interface**
   - Interactive mode
   - Rich terminal UI
   - Progress visualization
   - Color output

2. **Configuration**
   - Remote configuration sync
   - Environment-specific settings
   - Plugin system for custom handlers

3. **Advanced Features**
   - Backup compression
   - Backup rotation/cleanup
   - Remote backup locations
   - Backup verification
