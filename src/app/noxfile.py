import nox
from pathlib import Path
import os
import sys
import platform
import shutil
import subprocess
from typing import List, Optional
"""# Setup a complete new project
nox -s setup_project

# Run the test suite
nox -s test

# Format code
nox -s format

# Update dependencies
nox -s deps_update

# Run a specific version test
nox -s versioned -- 0.3.69

# Clean up all build artifacts
nox -s clean"""
# Default sessions to run when no session is specified
nox.options.sessions = ["lint", "type_check", "test"]
PYTHON_DEFAULT = "3.13"
# Check if UV is installed
def is_uv_installed() -> bool:
    """Check if UV is installed."""
    try:
        # Use the appropriate command based on platform
        if platform.system() == "Windows":
            subprocess.run(["uv.exe", "--version"], check=True, capture_output=True)
        else:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False
# Install UV if not already installed
def ensure_uv() -> None:
    """Ensure UV is installed."""
    if not is_uv_installed():
        print("UV not found. Installing UV...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
            print("UV installed successfully.")
        except subprocess.SubprocessError:
            print("Failed to install UV. Please install it manually: pip install uv")
            sys.exit(1)
# UV command helper function
def uv_cmd(cmd: List[str]) -> List[str]:
    """Return the appropriate UV command based on platform."""
    prefix = ["uv.exe"] if platform.system() == "Windows" else ["uv"]
    return prefix + cmd
@nox.session(python=PYTHON_DEFAULT)
def uvvenv(session: nox.Session) -> None:
    """Create a UV virtual environment and install the project in editable mode."""
    ensure_uv()
    # Create UV virtual environment
    session.run(*uv_cmd(["venv"]), external=True)
    # Install the project in development/editable mode
    session.run(*uv_cmd(["pip", "install", "-e", "."]), external=True)
    # Install development dependencies
    if Path("requirements-dev.txt").exists():
        session.run(*uv_cmd(["pip", "install", "-r", "requirements-dev.txt"]), external=True)
@nox.session(python=PYTHON_DEFAULT)
def lint(session: nox.Session) -> None:
    """Run linters on the codebase."""
    ensure_uv()
    session.install("ruff>=0.3.0")
    # Run Ruff linter and formatter
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
@nox.session(python=PYTHON_DEFAULT)
def format(session: nox.Session) -> None:
    """Format code with Ruff."""
    ensure_uv()
    session.install("ruff>=0.3.0")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
@nox.session(python=PYTHON_DEFAULT)
def type_check(session: nox.Session) -> None:
    """Run type checking with mypy."""
    ensure_uv()
    session.install("mypy>=1.8.0")
    # Add any type stubs needed
    session.install("types-requests", "types-pyyaml")
    # Get source directory from pyproject.toml or use default
    src_dir = "src"
    if Path("pyproject.toml").exists():
        import tomllib
        with open("pyproject.toml", "rb") as f:
            try:
                pyproject = tomllib.load(f)
                src_dir = pyproject.get("project", {}).get("src-path", "src")
            except Exception:
                pass
    session.run("mypy", src_dir)
@nox.session(python=PYTHON_DEFAULT)
def test(session: nox.Session) -> None:
    """Run the test suite with pytest."""
    ensure_uv()
    session.install("pytest>=8.0.0", "pytest-cov", "pytest-asyncio>=0.23.0")
    # Install the package and dependencies
    session.install("-e", ".")
    # Get test directory from pyproject.toml or use default
    test_dir = "tests"
    if Path("pyproject.toml").exists():
        import tomllib
        with open("pyproject.toml", "rb") as f:
            try:
                pyproject = tomllib.load(f)
                test_dir = pyproject.get("project", {}).get("tests-path", "tests")
            except Exception:
                pass
    # Run tests with coverage
    session.run(
        "pytest",
        "--cov=src",
        "--cov-report=term",
        "--cov-report=xml:coverage.xml",
        test_dir,
        *session.posargs
    )
@nox.session(python=PYTHON_DEFAULT)
def build(session: nox.Session) -> None:
    """Build the package."""
    ensure_uv()
    session.install("build>=1.0.3")
    session.run("python", "-m", "build")
@nox.session(python=PYTHON_DEFAULT)
def clean(session: nox.Session) -> None:
    """Clean build artifacts."""
    paths = [
        ".coverage",
        "coverage.xml",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "dist",
        "build",
        "*.egg-info",
        "**/__pycache__",
        "**/*.pyc",
    ]
    for path in paths:
        for p in Path(".").glob(path):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
@nox.session
@nox.parametrize("version", ["0.3.69"])
def versioned(session: nox.Session, version: str) -> None:
    """
    Run a versioned session.
    From the CLI: `nox -s versioned -- 0.3.69`
    """
    ensure_uv()
    session.install(f"cognosis=={version}")
    session.run("python", "-m", "demiurge")
@nox.session(python=PYTHON_DEFAULT)
def docs(session: nox.Session) -> None:
    """Build documentation."""
    ensure_uv()
    session.install("sphinx>=7.2.6", "sphinx-rtd-theme>=2.0.0")
    # Install the package to make its modules available for autodoc
    session.install("-e", ".")
    # Build the docs
    docs_dir = Path("docs")
    if not docs_dir.exists():
        # Create a basic docs structure if it doesn't exist
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "source").mkdir(exist_ok=True)
        session.run("sphinx-quickstart", "--no-sep", "-p", "Your Project", "-a", "Your Name", "docs")
    session.run("sphinx-build", "-b", "html", "docs/source", "docs/build/html")
@nox.session(python=PYTHON_DEFAULT)
def deps_update(session: nox.Session) -> None:
    """Update dependencies using UV."""
    ensure_uv()
    # Update requirements.txt
    if Path("requirements.txt").exists():
        session.run(*uv_cmd(["pip", "compile", "requirements.txt", "--upgrade", "--output-file", "requirements.lock"]), external=True)
        shutil.copy("requirements.lock", "requirements.txt")
    # Update dev requirements
    if Path("requirements-dev.txt").exists():
        session.run(*uv_cmd(["pip", "compile", "requirements-dev.txt", "--upgrade", "--output-file", "requirements-dev.lock"]), external=True)
        shutil.copy("requirements-dev.lock", "requirements-dev.txt")
@nox.session(python=PYTHON_DEFAULT)
def git_hooks(session: nox.Session) -> None:
    """Set up git hooks for the project."""
    ensure_uv()
    session.install("pre-commit>=3.6.0")
    # Create default pre-commit config if it doesn't exist
    if not Path(".pre-commit-config.yaml").exists():
        with open(".pre-commit-config.yaml", "w") as f:
            f.write("""repos:
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
    -   id: ruff
        args: [--fix, --exit-non-zero-on-fix]
    -   id: ruff-format

-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
    -   id: check-yaml
    -   id: end-of-file-fixer
    -   id: trailing-whitespace
    -   id: check-added-large-files
    -   id: debug-statements
    -   id: check-toml
""")
    
    session.run("pre-commit", "install")
    session.run("pre-commit", "autoupdate")
@nox.session(python=PYTHON_DEFAULT)
def setup_project(session: nox.Session) -> None:
    """Set up a new project with all the necessary files."""
    ensure_uv()
    # Create pyproject.toml if it doesn't exist
    if not Path("pyproject.toml").exists():
        session.log("Creating pyproject.toml")
        with open("pyproject.toml", "w") as f:
            f.write("""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "your-project-name"
version = "0.1.0"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
description = "A short description of your project"
readme = "README.md"
requires-python = ">=3.13"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "uvx>=0.1.0",
]
dev-dependencies = [
    "ruff>=0.3.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
]
src-path = "src"
tests-path = "tests"

[project.urls]
"Homepage" = "https://github.com/yourusername/your-project"
"Bug Tracker" = "https://github.com/yourusername/your-project/issues"

[tool.ruff]
line-length = 88
target-version = "py313"
select = ["E", "F", "I", "N", "W"]
ignore = []
fixable = ["A", "B", "C", "D", "E", "F", "I"]
""")
    # Create README.md if it doesn't exist
    if not Path("README.md").exists():
        session.log("Creating README.md")
        with open("README.md", "w") as f:
            f.write("""# Your Project Name

A short description of your project.

## Installation

```bash
pip install your-project-name
```

## Usage

```python
import your_package
# Your code here
```

## Development

This project uses nox for automation:

```bash
# Install development dependencies
nox -s uvvenv

# Run tests
nox -s test

# Run linters
nox -s lint

# Format code
nox -s format
```

## License

MIT
""")
    # Create src and tests directories
    Path("src").mkdir(exist_ok=True)
    Path("tests").mkdir(exist_ok=True)
    # Create __init__.py files
    Path("src/__init__.py").touch(exist_ok=True)
    Path("tests/__init__.py").touch(exist_ok=True)
    # Create a sample test
    if not Path("tests/test_sample.py").exists():
        with open("tests/test_sample.py", "w") as f:
            f.write("""def test_sample():
    assert True
""")
    # Initialize git if not already
    if not Path(".git").exists():
        session.run("git", "init", external=True)
        with open(".gitignore", "w") as f:
            f.write("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
coverage.xml
.tox/
.nox/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# mypy
.mypy_cache/

# ruff
.ruff_cache/

# IDE
.idea/
.vscode/
*.swp
*.swo
""")
    # Run the git hooks setup
    session.run("nox", "-s", "git_hooks")
    # Create initial virtual environment
    session.run("nox", "-s", "uvvenv")
    session.log("Project setup complete! You can now start development.")
