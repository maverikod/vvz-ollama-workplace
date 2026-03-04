#!/bin/sh
# Generate adapter config for local run. Run from project root.
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

CONFIG_DIR="${PROJECT_ROOT}/config"
CERTS_DIR="${PROJECT_ROOT}/mtls_certificates"
if [ ! -d "${CERTS_DIR}" ]; then
  CERTS_DIR="${PROJECT_ROOT}/docker/certs"
fi
mkdir -p "${CONFIG_DIR}"

export ADAPTER_CONFIG_PATH="${CONFIG_DIR}/adapter_config.json"
export CERTS_DIR
export ADAPTER_PORT="${ADAPTER_PORT:-8015}"
export ADVERTISED_HOST="${ADVERTISED_HOST:-localhost}"
export ADAPTER_LOG_DIR="${PROJECT_ROOT}/logs"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export MCP_PROXY_HOST="${MCP_PROXY_HOST:-mcp-proxy}"
export MCP_PROXY_PORT="${MCP_PROXY_PORT:-3004}"

mkdir -p "${ADAPTER_LOG_DIR}"

"${PROJECT_ROOT}/.venv/bin/python" "${PROJECT_ROOT}/docker/generate_config.py"
echo "Generated ${ADAPTER_CONFIG_PATH} (certs from ${CERTS_DIR})."
