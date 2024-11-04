import tomllib
from pathlib import Path

def get_version():
    root = Path(__file__).parent.parent.parent
    print(root)
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

__version__ = get_version()

__name__ += '.' + __version__  # Update USER module name with version

print(f'USER.{__name__}')

__all__ = []
__all__.append(__name__) # Add USER module name to __all__
