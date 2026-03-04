#!/bin/sh
# Start Redis, then OLLAMA, then MCP adapter. Configs/logs/models mounted from host.
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

# Regenerate config from env on every start (registration.server_id = ADVERTISED_HOST).
echo "Generating adapter config at ${CONFIG_PATH}..."
/app/.venv/bin/python /app/generate_config.py

echo "Starting Redis (data in /app/redis_data, mounted from host)..."
redis-server /app/redis.conf

# Keep models loaded: -1 = never unload (model starts with server and stays in memory).
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"
# Use mounted dir for models so they persist across container rebuilds (no re-download).
export OLLAMA_MODELS="${OLLAMA_MODELS:-/app/data}"
export OLLAMA_HOME="${OLLAMA_HOME:-/app/data}"
# Force CPU-only when OLLAMA_LLM_LIBRARY is set (e.g. cpu, cpu_avx2). Unset = use GPU if available.
if [ -n "${OLLAMA_LLM_LIBRARY:-}" ]; then
  export OLLAMA_LLM_LIBRARY
  echo "OLLAMA: CPU-only mode (OLLAMA_LLM_LIBRARY=${OLLAMA_LLM_LIBRARY})." >&2
fi

echo "Starting OLLAMA (KEEP_ALIVE=${OLLAMA_KEEP_ALIVE}, models stay loaded)..." >&2
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

# Pull and warm up models (comma-separated list from OLLAMA_PRELOAD_MODELS).
# Models load here and stay in memory (OLLAMA_KEEP_ALIVE=-1); adapter starts only after this.
if [ -n "${OLLAMA_PRELOAD_MODELS:-}" ]; then
  for model in $(echo "${OLLAMA_PRELOAD_MODELS}" | tr ',' ' '); do
    model=$(echo "$model" | tr -d ' ')
    [ -z "$model" ] && continue
    echo "Pulling model: ${model}..." >&2
    ollama pull "${model}" || true
    echo "Warming up model: ${model}..." >&2
    if curl -sf --max-time 300 -X POST http://127.0.0.1:11434/api/chat \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"${model}\",\"messages\":[{\"role\":\"user\",\"content\":\"Hi\"}],\"stream\":false}" \
      >/dev/null 2>&1; then
      echo "Warmed: ${model}" >&2
    else
      echo "Warm-up failed for ${model} (will retry in adapter)" >&2
    fi
  done
  echo "Preload done; models stay loaded (OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE})." >&2
fi

echo "Starting MCP adapter..." >&2
exec /app/.venv/bin/python /app/run_adapter.py --config "${CONFIG_PATH}"
