"""Configuration for dotfiles backup and restore."""

from pathlib import Path
from typing import Dict, List

# Configuration for each program's files to backup
BACKUP_CONFIGS = {
    'cursor': {
        'name': 'Cursor',
        'files': [
            '.cursorrules',
            '.cursorsettings',
        ],
        'directories': [
            '.cursor',
        ]
    },
    'windsurf': {
        'name': 'Windsurf',
        'files': [
            '.windsurfrules',
        ],
        'directories': []
    },
    'vscode': {
        'name': 'VSCode',
        'files': [],
        'directories': [
            '.vscode'
        ]
    },
    'git': {
        'name': 'Git',
        'files': [
            '.gitignore',
            '.gitmessage',
            '.gitattributes',
        ],
        'directories': []
    }
}

# Directory where backups will be stored
BACKUP_DIR = Path('backups')

def get_program_files(program: str) -> List[str]:
    """Get list of files to backup for a program."""
    if program not in BACKUP_CONFIGS:
        return []
    return BACKUP_CONFIGS[program]['files']

def get_program_dirs(program: str) -> List[str]:
    """Get list of directories to backup for a program."""
    if program not in BACKUP_CONFIGS:
        return []
    return BACKUP_CONFIGS[program]['directories']

def get_all_programs() -> List[str]:
    """Get list of all configured programs."""
    return list(BACKUP_CONFIGS.keys())

def get_program_name(program: str) -> str:
    """Get friendly name of a program."""
    return BACKUP_CONFIGS.get(program, {}).get('name', program)
