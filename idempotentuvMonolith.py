#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "flask==3.1.0",
#     "python-lsp-server==1.12.0",
# ]
# resolved-versions = {
#     "flask": "3.1.0",
#     "python-lsp-server": "1.12.0",
#     "werkzeug": "3.1.3",
#     "jinja2": "3.1.4",
#     "pluggy": "1.5.0",
# }
# resolved-hash = "sha256:a1b2c3d4e5f6..."
# */

from __future__ import annotations
import ast
import hashlib
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# 0.  Single source of truth: the comment block at the top of *this* file
# ------------------------------------------------------------------
_SELF = Path(__file__).resolve()
_COMMENT_RE = re.compile(r'# /\* script\s*\n(.*?)\n# \*/', re.S)
_TOML_RE = re.compile(r'dependencies\s*=\s*\[(.*?)\]', re.S)
_PKG_RE = re.compile(r'"([^"]+)"')
_RESOLVED_RE = re.compile(r'resolved-versions\s*=\s*(\{.*?\})', re.S)
_HASH_RE = re.compile(r'resolved-hash\s*=\s*"([^"]+)"')

# Mapping for packages whose import name differs from pip name
_IMPORT_MAP = {
    'python-lsp-server': 'pylsp',
    'flask': 'flask',
    # Add exceptions as needed: 'Pillow': 'PIL', 'opencv-python': 'cv2', etc.
}

def _read_deps() -> list[str]:
    """Return the list of *optional* third-party packages mentioned in the comment."""
    raw = _SELF.read_text(encoding='utf-8')
    match = _COMMENT_RE.search(raw)
    if not match:
        return []
    block = match[1]
    deps_match = _TOML_RE.search(block)
    if not deps_match:
        return []
    # Extract package names, stripping version specifiers
    full_deps = _PKG_RE.findall(deps_match[1])
    return [d.split('==')[0].split('>=')[0].split('<=')[0] for d in full_deps]

def _read_resolved() -> dict[str, str] | None:
    """Return the resolved-versions dict if present."""
    raw = _SELF.read_text(encoding='utf-8')
    match = _COMMENT_RE.search(raw)
    if not match:
        return None
    block = match[1]
    resolved_match = _RESOLVED_RE.search(block)
    if not resolved_match:
        return None
    try:
        return ast.literal_eval(resolved_match[1])
    except (SyntaxError, ValueError):
        return None

def _read_resolved_hash() -> str | None:
    """Return the resolved-hash if present."""
    raw = _SELF.read_text(encoding='utf-8')
    match = _COMMENT_RE.search(raw)
    if not match:
        return None
    block = match[1]
    hash_match = _HASH_RE.search(block)
    return hash_match[1] if hash_match else None

# ------------------------------------------------------------------
# 1.  Bootstrap: make sure uv has installed the optional set
# ------------------------------------------------------------------
def _ensure_uv_deps(verbose: bool = False) -> bool:
    """
    Install dependencies via uv. Returns True if successful, False otherwise.
    """
    deps = _read_deps()
    if not deps:
        return True  # No deps needed
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'uv', 'pip', 'install', *deps],
            check=True,
            capture_output=True,
            text=True,
        )
        if verbose:
            print(f"✓ Installed: {', '.join(deps)}", file=sys.stderr)
        return True
    except FileNotFoundError:
        if verbose:
            print("✗ uv not found - falling back to std-lib mode", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"✗ uv install failed: {e.stderr}", file=sys.stderr)
        return False

# ------------------------------------------------------------------
# 2.  Detect which personality we *can* have right now
# ------------------------------------------------------------------
_AVAIL: dict[str, Any] = {}

def _probe(verbose: bool = False) -> None:
    """
    Probe for available optional dependencies and populate _AVAIL with module objects.
    """
    for pkg_name in _read_deps():
        import_name = _IMPORT_MAP.get(pkg_name, pkg_name.replace('-', '_'))
        try:
            mod = __import__(import_name)
            _AVAIL[import_name] = mod
            if verbose:
                print(f"✓ {pkg_name} → {import_name}", file=sys.stderr)
        except ModuleNotFoundError:
            _AVAIL[import_name] = None
            if verbose:
                print(f"✗ {pkg_name} → {import_name} (not available)", file=sys.stderr)

# ------------------------------------------------------------------
# 3.  Re-exec helper (idempotent)
# ------------------------------------------------------------------
_IN_UV_ENV = os.getenv('UV_RUN') == '1'

def _reexec_if_needed(verbose: bool = False) -> None:
    """
    Re-exec under 'uv run' if needed, but only if deps are actually missing.
    """
    if _IN_UV_ENV:
        if verbose:
            print("Already in UV_RUN environment", file=sys.stderr)
        return
    
    # Fast path: try probing first without re-exec
    _probe(verbose=verbose)
    deps_needed = _read_deps()
    import_names_needed = [_IMPORT_MAP.get(d, d.replace('-', '_')) for d in deps_needed]
    
    if all(_AVAIL.get(name) is not None for name in import_names_needed):
        if verbose:
            print("All deps already available, skipping re-exec", file=sys.stderr)
        return
    
    # Slow path: install and re-exec
    if verbose:
        print("Re-executing under uv run...", file=sys.stderr)
    
    _ensure_uv_deps(verbose=verbose)
    os.environ['UV_RUN'] = '1'
    result = subprocess.run(
        [sys.executable, '-m', 'uv', 'run', str(_SELF), *sys.argv[1:]],
    )
    sys.exit(result.returncode)

# ------------------------------------------------------------------
# 4.  Do the dance once and only once
# ------------------------------------------------------------------
_VERBOSE = '--verbose' in sys.argv or '-v' in sys.argv
_reexec_if_needed(verbose=_VERBOSE)
_probe(verbose=_VERBOSE)

# ------------------------------------------------------------------
# 5.  Public façade for the rest of your monolith
# ------------------------------------------------------------------
class Deps:
    """Std-lib only gateway to optional dependencies."""
    pass

# Auto-populate Deps class attributes
for pkg_name in _read_deps():
    import_name = _IMPORT_MAP.get(pkg_name, pkg_name.replace('-', '_'))
    setattr(Deps, import_name, _AVAIL.get(import_name))

# ------------------------------------------------------------------
# 6.  Lock file management (VCS-agnostic)
# ------------------------------------------------------------------
def _compute_lock_hash(resolved: dict[str, str]) -> str:
    """Compute a deterministic hash of the resolved versions."""
    canonical = json.dumps(resolved, sort_keys=True)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"

def _get_current_resolved() -> dict[str, str]:
    """
    Query uv for the actual installed versions of all deps (including transitive).
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'uv', 'pip', 'freeze'],
            check=True,
            capture_output=True,
            text=True,
        )
        resolved = {}
        for line in result.stdout.strip().split('\n'):
            if '==' in line:
                pkg, ver = line.split('==', 1)
                resolved[pkg.lower()] = ver
        return resolved
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

def _update_lock_in_file(resolved: dict[str, str]) -> None:
    """
    Rewrite this file's comment block with updated resolved-versions and hash.
    """
    raw = _SELF.read_text(encoding='utf-8')
    match = _COMMENT_RE.search(raw)
    if not match:
        print("ERROR: Cannot find comment block to update", file=sys.stderr)
        return
    
    old_block = match[0]
    block_content = match[1]
    
    # Remove old resolved-versions and resolved-hash if present
    block_content = _RESOLVED_RE.sub('', block_content)
    block_content = _HASH_RE.sub('', block_content)
    
    # Add new resolved info
    resolved_str = json.dumps(resolved, indent=4, sort_keys=True)
    # Format as Python dict literal for better readability
    resolved_str = resolved_str.replace('{', '{\n#     ').replace('}', '\n# }')
    resolved_str = resolved_str.replace(',', ',\n#    ')
    resolved_str = resolved_str.replace('{\n#     ', '{').replace('\n# }', '}')
    resolved_str = resolved_str.replace('\n#    ', '\n#     ')
    
    new_hash = _compute_lock_hash(resolved)
    
    new_block_content = block_content.rstrip() + f'\n# resolved-versions = {resolved_str}\n# resolved-hash = "{new_hash}"\n'
    new_block = f'# /* script\n{new_block_content}# */'
    
    new_raw = raw.replace(old_block, new_block)
    _SELF.write_text(new_raw, encoding='utf-8')
    print(f"✓ Updated lock with {len(resolved)} packages (hash: {new_hash})", file=sys.stderr)

def _verify_lock() -> bool:
    """
    Check if current resolved versions match the lock.
    Returns True if valid, False if mismatch or missing.
    """
    stored_resolved = _read_resolved()
    stored_hash = _read_resolved_hash()
    
    if not stored_resolved or not stored_hash:
        return False
    
    # Verify hash
    computed_hash = _compute_lock_hash(stored_resolved)
    if computed_hash != stored_hash:
        print("✗ Lock hash mismatch - file may be corrupted", file=sys.stderr)
        return False
    
    # Verify actual installed versions match
    current = _get_current_resolved()
    for pkg, ver in stored_resolved.items():
        if current.get(pkg.lower()) != ver:
            print(f"✗ Version mismatch: {pkg} (locked={ver}, current={current.get(pkg.lower(), 'missing')})", file=sys.stderr)
            return False
    
    return True

def _lock_command() -> None:
    """Generate/update the lock based on current installed versions."""
    print("Resolving dependencies...", file=sys.stderr)
    _ensure_uv_deps(verbose=True)
    resolved = _get_current_resolved()
    
    # Filter to only deps we care about (direct + transitive)
    deps = _read_deps()
    if not resolved:
        print("✗ No packages resolved", file=sys.stderr)
        return
    
    _update_lock_in_file(resolved)
    
    # Commit to VCS if possible
    _vcs_commit_lock()

def _vcs_commit_lock() -> None:
    """
    Attempt to commit the lock update to version control (Fossil or Git).
    """
    commit_msg = f"Lock dependencies: {_read_resolved_hash()}"
    
    # Try Fossil first
    if (Path.cwd() / '.fslckout').exists() or (Path.cwd() / '_FOSSIL_').exists():
        try:
            subprocess.run(['fossil', 'commit', '-m', commit_msg, str(_SELF)], check=True)
            print("✓ Committed to Fossil", file=sys.stderr)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
    
    # Try Git
    if (Path.cwd() / '.git').exists():
        try:
            subprocess.run(['git', 'add', str(_SELF)], check=True)
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            print("✓ Committed to Git", file=sys.stderr)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
    
    print("⚠ No VCS detected or commit failed - lock updated but not committed", file=sys.stderr)

# ------------------------------------------------------------------
# 7.  CLI commands
# ------------------------------------------------------------------
if '--bootstrap' in sys.argv:
    print('Bootstrap complete. Optional packages:', [k for k, v in _AVAIL.items() if v is not None])
    sys.exit(0)

if '--lock' in sys.argv:
    _lock_command()
    sys.exit(0)

if '--verify-lock' in sys.argv:
    if _verify_lock():
        print("✓ Lock is valid", file=sys.stderr)
        sys.exit(0)
    else:
        print("✗ Lock is invalid or missing", file=sys.stderr)
        sys.exit(1)

if '--help' in sys.argv or '-h' in sys.argv:
    print("""
Usage: ./monolith.py [OPTIONS]

Options:
  --bootstrap      Show available optional packages
  --lock           Freeze current dependency versions into this file
  --verify-lock    Check if installed versions match lock
  --verbose, -v    Show detailed bootstrap info
  --help, -h       Show this help
    """.strip())
    sys.exit(0)

# ------------------------------------------------------------------
# 8.  Monolithic app (main)
# ------------------------------------------------------------------
if __name__ == '__main__':
    if Deps.flask:
        print("Flask is available!")
        # app = Deps.flask.Flask(__name__)
    else:
        print("Flask not available, using std-lib fallback")
    
    if Deps.pylsp:
        print("Python LSP Server is available!")
    else:
        print("Python LSP Server not available")
