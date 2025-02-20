# Development Dotfiles Manager

A specialized dotfiles management system for maintaining consistent configurations across multiple Cursor and Windsurf development repositories. This tool helps you keep your development environment consistent by easily backing up and restoring configuration files between different project repositories.

## Purpose

When working on multiple repositories for Cursor and Windsurf development, you often need consistent configuration files across projects. This tool allows you to:
- Backup configuration files from a working repository
- Restore those configurations to other repositories
- Maintain consistency across your development environment

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

## Usage

### Backup Configuration

To backup configurations from a development repository:

```bash
python backup.py
```

The script will:
1. Show you available sibling Git repositories
2. Let you select the source repository
3. Backup all relevant configuration files
4. Store them organized by program type

### Restore Configuration

To restore configurations to another repository:

```bash
python restore.py
```

The script will:
1. Show available configuration backups
2. Let you select which backup to use
3. Show available target repositories
4. Warn about any existing files
5. Restore after confirmation

## Directory Structure

```
parent_directory/
├── dotfiles/                    # This management repo
│   ├── backups/
│   │   └── repo_name/          # One backup per repo
│   │       ├── cursor/         # Cursor configs
│   │       ├── windsurf/       # Windsurf configs
│   │       ├── vscode/         # VSCode settings
│   │       └── git/            # Git configs
│   ├── backup.py
│   ├── restore.py
│   └── config.py
├── project1/                    # Sibling development repo
├── project2/                    # Another development repo
└── [other repos...]
```

## Adding New Configuration Types

Edit `config.py` to add support for new configuration files:

```python
BACKUP_CONFIGS = {
    'new_tool': {
        'name': 'New Tool',
        'files': [
            '.toolconfig',
            '.toolrules',
        ],
        'directories': [
            '.tool_dir',
        ]
    },
}
```

## Requirements

- Python 3.6+
- No external dependencies

## Important Notes

- Maintains one backup per repository
- Only works with Git repositories as siblings
- Provides warnings before overwriting existing files
- Preserves file permissions during backup/restore

## Future Enhancements

- Support for additional development tools
- Backup history with timestamps
- Configuration templates
- Automatic backup on repository changes
