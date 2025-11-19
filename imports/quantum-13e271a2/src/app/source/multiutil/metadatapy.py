from importlib.metadata import distributions
"""`importlib.metadata` is part of Python's standard library (since 3.8) and is used to access package metadata,
including entry points, version info, and other package-specific data that resides in `.dist-info`."""
for dist in distributions():
    print(
        f"Package: {dist.metadata['Name']}, Version: {dist.metadata['Version']}")
