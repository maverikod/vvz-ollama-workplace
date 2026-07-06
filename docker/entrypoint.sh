#!/bin/sh
# Start Redis, then MCP adapter. Model access is delegated to the external
# model-access-core server (no local model process). Configs/logs mounted from host.
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

echo "Starting MCP adapter..." >&2
exec /app/.venv/bin/python /app/run_adapter.py --config "${CONFIG_PATH}"
