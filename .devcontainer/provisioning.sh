#!/bin/bash
FILE=$1

echo "Initializing Python bridge..."

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

sleep 2
# LSP server check
PORT=2087
if nc -z localhost $PORT; then
  echo "✅ pylsp server already listening on $PORT"
else
  echo "⚠️  pylsp not running yet, will try to start"
fi
sleep 2
curl -v http://localhost:2087 || echo "pylsp not responding"