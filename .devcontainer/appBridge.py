import tomllib
import sys
import os

# there is one source of truth; the pyproject.toml, so we use a python script @ build.
msc = {}


def extract_version(file_path):
    try:
        with open(file_path, "rb") as f:
            pyproject = tomllib.load(f)
        version = pyproject["project"]["version"]
        msc = pyproject.get("tool", {}).get("msc", {})
        print(f"Additional MSC configs: {msc}")
        print(version)
    except FileNotFoundError:
        print(
            f"[WARN] {file_path} not found. Skipping version extraction.",
            file=sys.stderr,
        )
        sys.exit(0)
    except KeyError as e:
        print(f"[WARN] Missing key in {file_path}: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        file_path = sys.argv[1]
    else:
        file_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    extract_version(file_path)
