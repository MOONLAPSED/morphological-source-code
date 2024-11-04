import os
import tomllib
from pathlib import Path
import hashlib

if __name__ == "__main__":
    print(f'{__file__} is not a module init, utilize the init in directory above.')

def get_version():
    root = Path(__file__).parent.parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def hash_file(filepath):
    """Generate SHA-256 hash for a given file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def hash_directory(directory):
    """Generate a combined SHA-256 hash for all files in a directory."""
    combined_hash = hashlib.sha256()
    for root, _, files in os.walk(directory):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            combined_hash.update(hash_file(filepath).encode())
    return combined_hash.hexdigest()

__all__ = []
__version__ = get_version()
__name__ += '.' + __version__  # Update USER module name with version
__all__.append(f'USER.{__name__}') # Add USER module name to __all__
