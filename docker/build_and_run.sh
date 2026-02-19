#!/bin/sh
# Build image, stop old container, run new one on network smart-assistant.
# Run from project root: ./docker/build_and_run.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Container name from config (single source for advertised hostname)
if [ -f "${SCRIPT_DIR}/run.conf" ]; then
  . "${SCRIPT_DIR}/run.conf"
fi
IMAGE_NAME="${IMAGE_NAME:-ollama-adapter}"
CONTAINER_NAME="${CONTAINER_NAME:-ollama-adapter}"
NETWORK_NAME="${NETWORK_NAME:-smart-assistant}"

CONFIG_DIR="${SCRIPT_DIR}/config"
LOGS_DIR="${SCRIPT_DIR}/logs"
CACHE_DIR="${SCRIPT_DIR}/cache"
DATA_DIR="${SCRIPT_DIR}/data"
# OLLAMA models and runtime data live in DATA_DIR; mount persists across builds
MODELS_AND_DATA_DIR="${DATA_DIR}"
CERTS_DIR="${SCRIPT_DIR}/certs"
# Prefer mtls_certificates (proxy-trusted certs) when present
MTLS_DIR="${PROJECT_ROOT}/mtls_certificates"
if [ -f "${MTLS_DIR}/ca.crt" ] && [ -f "${MTLS_DIR}/client.crt" ] && [ -f "${MTLS_DIR}/client.key" ] && [ -f "${MTLS_DIR}/server.crt" ] && [ -f "${MTLS_DIR}/server.key" ]; then
  CERTS_DIR="${MTLS_DIR}"
  echo "Using certs from mtls_certificates/ (proxy-trusted)."
fi

# Create all mounted dirs so host paths exist; data dir keeps OLLAMA models between runs
for d in "${CONFIG_DIR}" "${LOGS_DIR}" "${CACHE_DIR}" "${DATA_DIR}" "${SCRIPT_DIR}/certs"; do
  mkdir -p "$d"
done

# Mounts: certs, config, cache, logs, data. Run as user:group 1000:1000.
echo "Building image ${IMAGE_NAME}..."
docker build -f docker/Dockerfile -t "${IMAGE_NAME}" .

echo "Stopping old container ${CONTAINER_NAME} (if any)..."
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

echo "Starting container ${CONTAINER_NAME} on network ${NETWORK_NAME}..."
# User 1000:1000. Mounted dirs persist across rebuilds; OLLAMA models live in /app/data (DATA_DIR).
docker run -d \
  --name "${CONTAINER_NAME}" \
  --network "${NETWORK_NAME}" \
  -p 8015:8015 \
  -u 1000:1000 \
  -v "${CERTS_DIR}:/app/certs:ro" \
  -v "${CONFIG_DIR}:/app/config" \
  -v "${CACHE_DIR}:/app/cache" \
  -v "${LOGS_DIR}:/app/logs" \
  -v "${MODELS_AND_DATA_DIR}:/app/data" \
  -e CERTS_DIR=/app/certs \
  -e ADAPTER_PORT=8015 \
  -e ADVERTISED_HOST="${CONTAINER_NAME}" \
  -e OLLAMA_MODELS=/app/data \
  -e OLLAMA_HOME=/app/data \
  -e HOME=/app/data \
  -e OLLAMA_PRELOAD_MODELS="${OLLAMA_PRELOAD_MODELS:-llama3.2,qwen3}" \
  "${IMAGE_NAME}"

echo "Done. Container ${CONTAINER_NAME} is running (adapter https port 8015, user 1000:1000)."
echo "Mounts (model and data persist in data/): certs=${CERTS_DIR}, config=${CONFIG_DIR}, cache=${CACHE_DIR}, logs=${LOGS_DIR}, data=${DATA_DIR}"
