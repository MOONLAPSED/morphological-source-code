import os
import tomllib
from pathlib import Path
import hashlib

def get_version(level=0):
    """
    Gets the project version from pyproject.toml.

    Args:
        level (int, optional): The depth of the directory you're in relative to the root of the project.
                               Defaults to 0.

    Returns:
        str: The project version extracted from pyproject.toml.
    """
    current_path = Path(__file__).resolve().parent
    for _ in range(level):
        current_path = current_path.parent

    pyproject_path = current_path / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path, 'rb') as f:
        project_data = tomllib.load(f)
        return project_data["project"]["version"]

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

__all__ = ['get_version', 'hash_directory', 'hash_file']
__version__ = get_version(2)

if __name__ == "__main__":
    print(f'{__file__} is not a package init, utilize the init in directory above.')
    __all__ = []
    __version__ = get_version(2)
    __name__ += '.' + __version__  # Update USER module name with version
    __name__ = (f'USER.{__name__}') 
    __all__.append(__name__) # Add USER module name to __all__
    print(__name__)
    print(__all__)


# Passive runtime typing and permissions system via "__name__".
# Using 'generator'-style 'versioning' - internal versioning
# which is implicit in all IPC and message passing
elif __name__ == f"ADMIN.__main__.{__version__}":
    pass

elif __name__ == f"USER.__main__.{__version__}":
    pass

elif __name__ == f"__main__.{__version__}":
    pass

elif __name__ == "src.version":
    # print('hello ADMIN!') # logic here will execute when /__init__.py is invoked regardless of ADMIN/USER
    pass

elif __name__ == "src.version.__init__":
    # print('hello ADMIN!') # logic here will execute when /__init__.py is invoked regardless of ADMIN/USER
    pass

else:
    print(f'Sandboxed USER: {__name__}')