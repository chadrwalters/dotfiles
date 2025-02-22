# Product Requirements Document: Dotfiles CLI Tool

## Product Overview

### Problem Statement
The current cursor-tools system has limitations in handling complex repository structures, particularly:
1. Multiple separate Python scripts leading to maintenance overhead
2. Limited to sibling-level repository operations
3. No support for branch-specific configurations
4. Conflicts with Raycast extension submission requirements
5. Lack of granular program-specific operations

### Solution
A unified CLI tool (`dotfiles`) that provides:
- Single entry point for all operations
- Branch-aware configuration management
- Selective program operations
- Raycast-compatible workflow
- Improved repository structure handling

## User Stories

### 1. Unified Command Interface
**As a** developer
**I want to** use a single command for all configuration management
**So that** I can work more efficiently with a consistent interface

#### Acceptance Criteria
- Single `dotfiles` command with subcommands
- Consistent argument structure across subcommands
- Clear help and usage information
- Intuitive command naming

### 2. Branch-Specific Configuration Management
**As a** developer working with multiple branches
**I want to** maintain different configurations for different branches
**So that** I can have branch-specific development environments

#### Acceptance Criteria
- Can detect and list all branches in sibling repositories
- Can backup/restore configurations for specific branches
- Maintains separate backup directories for each branch
- Provides clear branch selection interface

### 3. Raycast Extension Development
**As a** Raycast extension developer
**I want to** maintain development configurations without violating submission rules
**So that** I can efficiently develop while ensuring store compliance

#### Acceptance Criteria
- Automatically excludes development configurations from submissions
- Maintains development files locally
- No manual file deletion required
- Compatible with Raycast's submission process

### 4. Selective Program Operations
**As a** developer
**I want to** backup/restore specific program configurations
**So that** I can manage configurations more granularly

#### Acceptance Criteria
- Can specify program via command line argument
- Validates program selection
- Clear feedback on program-specific operations
- Maintains existing bulk operation capability

## Feature Requirements

### 1. Command Line Interface
- Single entry point (`dotfiles` command)
- Subcommands for different operations
- Consistent argument structure
- Help and usage documentation

### 2. Enhanced Repository Detection
- Recursive Git repository scanning
- Branch detection and management
- Repository path validation
- Error handling for invalid repositories

### 3. Branch-Aware Operations
- Branch-specific backup structure
- Branch selection interface
- Branch metadata storage
- Cross-branch operation support

### 4. Raycast Compatibility
- Git attributes integration
- Automatic file exclusion
- Local development file preservation
- Submission preparation support

### 5. Program-Specific Operations
- Command-line program selection
- Program validation
- Selective backup/restore
- Operation feedback

## Constraints and Limitations

### 1. Technical Constraints
- Python 3.8+ compatibility
- UV for dependency and environment management
- Git command-line tools
- File system permissions
- Cross-platform compatibility

### 2. Legacy Compatibility Requirements
- Must maintain existing backup structure
- Must support reading from existing backups
- Must preserve all current functionality
- Must support all existing configuration types

### 3. User Requirements
- Git knowledge requirement
- Command-line familiarity
- Repository structure requirements
- Program configuration knowledge

### 4. Development Requirements
- Type hints for all Python code
- Comprehensive test coverage
- Documentation for all features
- Clean code formatting and linting
