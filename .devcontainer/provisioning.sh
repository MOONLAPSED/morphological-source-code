#!/bin/bash
FILE=$1

echo "Initializing..."

# connectivity check
if curl -fsSL https://example.com >/dev/null; then
  echo "✅ internet OK"
else
  echo "❌ internet down"
fi

# "portsAttributes": {
#   "8000": { "label": "App Server", "onAutoForward": "openBrowser" },
#   "8888": { "label": "Jupyter", "onAutoForward": "notify" }
# }
