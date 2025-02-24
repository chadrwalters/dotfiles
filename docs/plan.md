Packing repository using repomix...
Error: rootDirs.map is not a function

# Refactoring Plan: Simplified Backup/Restore Interface

## Overview
We want to simplify the interface for backup/restore while keeping our smart configuration system. The goal is to have two simple operations:

1. **Backup**: Given a source directory, back up all configured files (from programs defined in config) into a timestamped backup
2. **Restore**: Given a backup directory and target directory, restore all configured files to their proper locations

## Current Issues
- Bootstrap functionality adds unnecessary complexity
- Command interface is too complex with too many options
- Restore/bootstrap logic is confusing and overlapping

## Implementation Plan

### 1. Directory Structure (Keep As Is)
```
backups/
└── repo_name/
    └── YYYYMMDD-HHMMSS/
        ├── cursor/
        │   ├── .cursorrules
        │   └── .cursor/
        ├── vscode/
        │   └── .vscode/
        └── git/
            └── .gitconfig
```

### 2. Code Changes

#### Phase 1: Remove Bootstrap
1. Delete:
   - `src/dotfiles/core/bootstrap.py`
   - Remove bootstrap command from CLI
   - Remove bootstrap-related tests

#### Phase 2: Simplify Backup Manager
1. Update `BackupManager` class interface:
   ```python
   class BackupManager:
       def __init__(self, config: Config):
           self.config = config
           self.backup_dir = Path("backups")

       def backup(self, source_dir: Path) -> Path:
           """
           Backup configured files from source directory
           Returns the backup directory path
           """
           if not source_dir.exists():
               raise ValueError(f"Source directory {source_dir} does not exist")

           # Use existing config to determine which files to backup
           repo = GitRepository(source_dir)
           timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
           backup_path = self.backup_dir / repo.name / timestamp

           # Use existing program config but simplify the interface
           for program, config in self.config.programs.items():
               self.backup_program(repo, program, backup_path)

           console.print(f"[green]Backed up {source_dir} to {backup_path}")
           return backup_path

       def list_backups(self, repo_name: Optional[str] = None) -> List[Path]:
           """List available backups for a repo or all repos"""
           backups = []
           if repo_name:
               repo_dir = self.backup_dir / repo_name
               if repo_dir.exists():
                   backups.extend(sorted(repo_dir.glob("*/*"), reverse=True))
           else:
               for repo_dir in self.backup_dir.iterdir():
                   if repo_dir.is_dir():
                       backups.extend(sorted(repo_dir.glob("*/*"), reverse=True))
           return backups
   ```

#### Phase 3: Simplify Restore Manager
1. Update `RestoreManager` class:
   ```python
   class RestoreManager:
       def __init__(self, config: Config):
           self.config = config

       def restore(self, backup_path: Path, target_dir: Path) -> bool:
           """
           Restore files from backup to target directory
           Uses config to know where each file should go
           """
           if not backup_path.exists():
               raise ValueError(f"Backup directory {backup_path} does not exist")
           if not backup_path.is_dir():
               raise ValueError(f"{backup_path} is not a directory")

           # Create target if needed
           target_dir.mkdir(parents=True, exist_ok=True)

           # Use existing program config to restore files to correct locations
           for program_dir in backup_path.iterdir():
               if not program_dir.is_dir():
                   continue

               program = program_dir.name
               program_config = self.config.get_program_config(program)
               if not program_config:
                   continue

               self.restore_program(program_dir, target_dir, program_config)

           console.print(f"[green]Restored files to {target_dir}")
           return True
   ```

#### Phase 4: Update CLI Interface
1. Update `cli.py`:
   ```python
   @click.group()
   def cli():
       """Dotfiles management tool"""

   @cli.command()
   @click.argument("source_dir")
   def backup(source_dir: str):
       """Backup configured files from directory"""
       config = Config()
       manager = BackupManager(config)
       manager.backup(Path(source_dir))

   @cli.command()
   @click.argument("backup_dir")
   @click.argument("target_dir")
   def restore(backup_dir: str, target_dir: str):
       """Restore files from backup to target directory"""
       config = Config()
       manager = RestoreManager(config)
       manager.restore(Path(backup_dir), Path(target_dir))

   @cli.command()
   @click.argument("repo", required=False)
   def list(repo: Optional[str]):
       """List available backups"""
       config = Config()
       manager = BackupManager(config)
       backups = manager.list_backups(repo)

       # Show backups with their timestamps and available programs
       for backup in backups:
           print(f"\n{backup.parent.parent.name} ({backup.name}):")
           for program_dir in backup.iterdir():
               if program_dir.is_dir():
                   print(f"  - {program_dir.name}")
   ```

### 3. Testing Strategy
1. Update test suite:
   - Remove bootstrap tests
   - Keep config-related tests
   - Keep program-specific backup tests
   - Add tests for proper file placement during restore
   - Add tests for error handling in both backup and restore

## Benefits
- Simpler user interface
- Maintains smart configuration system
- More predictable behavior
- Easier to understand and use
- Still preserves all program-specific file handling

## Timeline
1. Remove bootstrap: 1 day
2. Update backup/restore: 2 days
3. Update CLI: 1 day

Total: 4 days
