#!/bin/sh
# Start OLLAMA in container, then run MCP adapter with auto-registration.
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

CERTS_DIR="${CERTS_DIR:-/app/certs}"
CONFIG_PATH="${ADAPTER_CONFIG_PATH:-/app/config/adapter_config.json}"
export ADAPTER_CONFIG_PATH="${CONFIG_PATH}"
export CERTS_DIR

# Certs are mounted (generated once outside the image). Do not generate in container.
if [ ! -f "${CERTS_DIR}/ca.crt" ] || [ ! -f "${CERTS_DIR}/server.crt" ] || [ ! -f "${CERTS_DIR}/server.key" ] || [ ! -f "${CERTS_DIR}/client.crt" ] || [ ! -f "${CERTS_DIR}/client.key" ]; then
  echo "Error: required certs not found in ${CERTS_DIR}. Generate once (e.g. mtls_certificates/generate_certs.sh) and mount: ca.crt, server.crt, server.key, client.crt, client.key." >&2
  exit 1
fi

if [ ! -f "${CONFIG_PATH}" ]; then
  echo "Generating adapter config at ${CONFIG_PATH}..."
  /app/.venv/bin/python /app/generate_config.py
fi

echo "Starting OLLAMA in container..."
ollama serve &
OLLAMA_PID=$!
# Wait for Ollama to listen (up to 30s)
i=0
while [ $i -lt 30 ]; do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 $OLLAMA_PID 2>/dev/null; then
    echo "OLLAMA process exited." >&2
    exit 1
  fi
  sleep 1
  i=$((i + 1))
done
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "OLLAMA did not become ready in time." >&2
  exit 1
fi

# Use mounted dir for models so they persist across container rebuilds (no re-download).
export OLLAMA_MODELS="${OLLAMA_MODELS:-/app/data}"
export OLLAMA_HOME="${OLLAMA_HOME:-/app/data}"

# Ensure models from config are present: check, log and pull missing ones.
/app/.venv/bin/python /app/ensure_ollama_models.py

echo "Starting MCP adapter (auto-registration enabled)..."
exec /app/.venv/bin/python /app/run_adapter.py --config "${CONFIG_PATH}"
