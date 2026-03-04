#!/bin/sh
# Start OLLAMA in container, then run MCP adapter with auto-registration.
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

CERTS_DIR="${CERTS_DIR:-/app/certs}"
CONFIG_PATH="${ADAPTER_CONFIG_PATH:-/app/config/adapter_config.json}"
export ADAPTER_CONFIG_PATH="${CONFIG_PATH}"
export CERTS_DIR

# 1. Generate certs if missing (for mTLS server + registration client)
if [ ! -f "${CERTS_DIR}/ca.crt" ]; then
  echo "Generating mTLS certificates in ${CERTS_DIR}..."
  /app/generate_certs.sh "${CERTS_DIR}"
fi

# 2. Generate adapter config (uses SimpleConfigGenerator; includes registration)
if [ ! -f "${CONFIG_PATH}" ]; then
  echo "Generating adapter config at ${CONFIG_PATH}..."
  /app/.venv/bin/python /app/generate_config.py
fi

# 3. Start OLLAMA inside container (used by adapter at 127.0.0.1:11434)
echo "Starting OLLAMA in container..."
ollama serve &
OLLAMA_PID=$!
sleep 3
if ! kill -0 $OLLAMA_PID 2>/dev/null; then
  echo "OLLAMA failed to start." >&2
  exit 1
fi

# 4. Run adapter (lifespan will auto-register with proxy when registration.enabled=true)
echo "Starting MCP adapter (auto-registration enabled)..."
exec /app/.venv/bin/python /app/run_adapter.py --config "${CONFIG_PATH}"
