#!/bin/bash
FILE=$1

echo "Initializing Python bridge..."

if [ -f "./scripts/appBridge.py" ] && [ -f "pyproject.toml" ]; then
  VERSION=$(python3 ./scripts/appBridge.py)
  echo "Detected version: $VERSION"
else
  echo "[WARN] pyproject.toml or appBridge.py not found. Skipping version extraction."
fi

echo "[PYTHON] Sending version $version to Python"

# Assuming the version is sent as a JSON object
echo "{\"version\": \"$version\"}" | python3 -u main.py