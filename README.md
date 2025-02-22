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
# List available repositories
dotfiles list repos

# List available backups
dotfiles list backups

# Backup configurations
dotfiles backup [--repo REPO] [--program PROGRAM]

# Restore configurations
dotfiles restore [--repo REPO] [--program PROGRAM]

# Bootstrap a new repository
dotfiles bootstrap [--repo REPO] [--template TEMPLATE]

# Wipe configurations
dotfiles wipe [--repo REPO] [--program PROGRAM]
```

### Branch-Specific Operations

```bash
# Backup configurations from specific branch
dotfiles backup --repo REPO --branch BRANCH

# Restore configurations to specific branch
dotfiles restore --repo REPO --branch BRANCH
```

### Program-Specific Operations

```bash
# Backup specific program configurations
dotfiles backup --program cursor

# Restore specific program configurations
dotfiles restore --program vscode
```

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

## Legacy Support

The tool maintains compatibility with existing backup structures and supports all legacy functionality. Legacy Python scripts are preserved in the `legacy/` directory:

- `legacy/backup.py` - Original backup script
- `legacy/restore.py` - Original restore script
- `legacy/bootstrap.py` - Original bootstrap script
- `legacy/wipe.py` - Original wipe script
- `legacy/config.py` - Original configuration script
- `legacy/backups_archive/` - Archive of original backups

To use legacy scripts (not recommended for new operations):
```bash
python legacy/backup.py
python legacy/restore.py
python legacy/bootstrap.py
python legacy/wipe.py
```

## Directory Structure

```
dotfiles/
├── src/
│   └── dotfiles/           # Main package
│       ├── __init__.py
│       ├── cli.py          # CLI implementation
│       ├── core/           # Core functionality
│       └── utils/          # Utility functions
├── tests/                  # Test suite
├── backups/               # Backup storage
├── legacy/                # Legacy code and backups
├── docs/                  # Documentation
├── pyproject.toml        # Project configuration
├── README.md
└── LICENSE
```

## Contributing

1. Fork the repository
2. Create a virtual environment with UV
3. Install development dependencies: `uv pip install -e ".[dev]"`
4. Make your changes
5. Run tests: `pytest`
6. Run formatters and linters:
   ```bash
   black .
   isort .
   ruff check .
   mypy .
   ```
7. Submit a pull request

## License

See [LICENSE](LICENSE) file.
