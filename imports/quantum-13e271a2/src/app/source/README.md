# Project Manager for Python 3.13

A comprehensive cross-platform tool for managing Python 3.13 projects with UV package management, supporting both Windows 11 and Ubuntu 22.04.

## Overview

This Project Manager streamlines the development, administration, and deployment of Python 3.13 projects using UV (a faster alternative to pip). It handles configuration management, dependency tracking, environment setup, and provides utility functions for common development tasks across different platforms.

## Features

- ✅ Cross-platform support (Windows 11 and Ubuntu 22.04)
- ✅ UV-based package management
- ✅ Multiple operation modes (DEV, ADMIN, USER)
- ✅ Automatic environment setup and teardown
- ✅ Dependency management and locking
- ✅ Code linting and formatting using Ruff
- ✅ Test running with pytest
- ✅ Module scaffolding
- ✅ Project configuration via pyproject.toml and demiurge.json

## Installation

### Prerequisites

- Python 3.13 or later
- [UV](https://github.com/astral-sh/uv) package manager

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/project-manager.git
   cd project-manager
   ```

2. Run in dev mode to set up the environment:
   ```bash
   python main.py DEV
   ```

## Usage

### Command Structure

```
python main.py [--root ROOT_DIR] [mode] [--timeout SECONDS] [--create-module MODULE_NAME]
```

#### nox session management

# Setup a complete new project
`nox -s setup_project`

# Run the test suite
`nox -s test`

# Format code
`nox -s format`

# Update dependencies
`nox -s deps_update`

# Run a specific version test
`nox -s versioned -- 0.3.69`

# Clean up all build artifacts
`nox -s clean`

### Operation Modes

The tool supports the following modes:

| Mode | Description |
|------|-------------|
| `DEV` | Development mode - Sets up environment, installs dependencies, runs tests and linters |
| `ADMIN` | Admin mode - Performs administrative tasks and platform-specific configurations |
| `USER` | User mode - Minimal setup for running the application |
| `TEARDOWN` | Cleans up environment and temporary files |
| `UPGRADE` | Upgrades all dependencies to their latest versions |

### Examples

#### Setup Development Environment
```bash
python main.py DEV
```

#### Create a New Module
```bash
python main.py --create-module my_module
```

#### Run in User Mode with a Different Root Directory
```bash
python main.py --root /path/to/project USER
```

#### Upgrade Dependencies
```bash
python main.py UPGRADE
```

#### Teardown Environment
```bash
python main.py TEARDOWN
```

## Configuration

### pyproject.toml

The project uses `pyproject.toml` for primary configuration:

```toml
[project]
name = "your-project-name"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "uvx>=0.1.0",
]
dev-dependencies = [
    "ruff>=0.3.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0"
]
ffi-modules = []
src-path = "src"
tests-path = "tests"

[tool.ruff]
line-length = 88
target-version = "py313"
select = ["E", "F", "I", "N", "W"]
ignore = []
fixable = ["A", "B", "C", "D", "E", "F", "I"]
```

### demiurge.json

Platform-specific and additional configurations are stored in `demiurge.json`:

```json
{
    "ffi_modules": [],
    "src_path": "src",
    "dev_dependencies": [],
    "profile_enabled": true,
    "platform_specific": {
        "windows": {
            "priority": 32
        },
        "linux": {
            "priority": 0
        }
    }
}
```

## Directory Structure

The Project Manager creates and maintains the following directory structure:

```
project-root/
├── pyproject.toml
├── config.json
├── requirements.txt
├── requirements-dev.txt
├── requirements.lock
├── requirements-dev.lock
├── src/
│   ├── __init__.py
│   ├── ffi/
│   │   └── __init__.py
│   └── your_modules/
└── tests/
    ├── __init__.py
    └── test_*.py
```

## Style Guide

### Code Style

This project follows these coding conventions:

1. **PEP 8** compliant with Ruff enforcement
2. Line length limited to 88 characters
3. Type annotations for all function parameters and return values
4. Docstrings for all modules, classes, and functions

### Coding Principles

- **DRY (Don't Repeat Yourself)**: Avoid code duplication
- **Single Responsibility**: Each function/class should do one thing well
- **Error Handling**: Always handle exceptions and provide meaningful error messages
- **Platform Independence**: Write code that works on both Windows and Linux 
- **Asynchronous by Default**: Use asyncio for I/O-bound operations

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat: add new module creation feature
fix: correct path handling on Windows
docs: update README with examples
test: add tests for admin mode
refactor: improve command execution logic
```

### Module Structure

When creating new modules with `--create-module`, follow this structure:

1. Main functionality in `module_name.py`
2. `__init__.py` for package exports
3. Test file in `tests/test_module_name.py`

## Development Workflow

1. **Setup**: Run `python main.py DEV` to set up the environment
2. **Create Module**: Use `python main.py --create-module my_feature` to scaffold new modules
3. **Run Tests**: Use `python main.py DEV` to run tests (or directly with pytest)
4. **Format Code**: Automatically done in DEV mode, or run Ruff manually
5. **Upgrade**: Run `python main.py UPGRADE` when you want to update dependencies

## UV Package Management

This project uses [UV](https://github.com/astral-sh/uv) for fast, reliable Python package management. Key UV commands:

- `uv venv` - Create a virtual environment
- `uv pip install` - Install packages
- `uv pip compile` - Create lock files from requirements
- `uvx run` - Run commands in the virtual environment

## Platform-Specific Notes

### Windows 11

- Commands use `.exe` extension 
- Shell execution is used when needed for PATH resolution
- Default process priority is set to 32

### Ubuntu 22.04

- Commands don't use file extensions
- Process priority is set to 0 by default
- Uses direct command execution

## Troubleshooting

### Common Issues

1. **"Command not found"**: Ensure UV is installed and in your PATH
2. **Permission errors on Linux**: You may need to use `sudo` for certain operations
3. **Timeout errors**: Increase timeout with `--timeout` flag for slow operations

### Debugging

Set the logger level to DEBUG for more verbose output:

```python
logger.setLevel(logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-branch`
3. Make your changes following the style guide
4. Submit a pull request with a detailed description

## License

This project is licensed under the MIT License - see the LICENSE file for details.