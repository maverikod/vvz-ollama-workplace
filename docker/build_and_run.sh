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
# Step 15 runtime contract: network is fixed and mandatory.
NETWORK_NAME="smart-assistant"

CONFIG_DIR="${SCRIPT_DIR}/config"
LOGS_DIR="${SCRIPT_DIR}/logs"
CACHE_DIR="${SCRIPT_DIR}/cache"
DATA_DIR="${SCRIPT_DIR}/data"
# Redis persistence (bases); OLLAMA models and runtime in DATA_DIR
REDIS_DATA_DIR="${SCRIPT_DIR}/redis_data"
MODELS_AND_DATA_DIR="${DATA_DIR}"
CERTS_DIR="${SCRIPT_DIR}/certs"
# Prefer mtls_certificates (proxy-trusted certs) when present
MTLS_DIR="${PROJECT_ROOT}/mtls_certificates"
if [ -f "${MTLS_DIR}/ca.crt" ] && [ -f "${MTLS_DIR}/client.crt" ] && [ -f "${MTLS_DIR}/client.key" ] && [ -f "${MTLS_DIR}/server.crt" ] && [ -f "${MTLS_DIR}/server.key" ]; then
  CERTS_DIR="${MTLS_DIR}"
  echo "Using certs from mtls_certificates/ (proxy-trusted)."
fi

# Create all mounted dirs so host paths exist (bases, configs, logs, models)
for d in "${CONFIG_DIR}" "${LOGS_DIR}" "${CACHE_DIR}" "${DATA_DIR}" "${REDIS_DATA_DIR}" "${SCRIPT_DIR}/certs"; do
  mkdir -p "$d"
done

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  echo "Creating required docker network ${NETWORK_NAME}..."
  docker network create "${NETWORK_NAME}" >/dev/null
fi

# Mounts: certs, config, cache, logs, data. Run as user:group 1000:1000.
echo "Building image ${IMAGE_NAME}..."
docker build -f docker/Dockerfile -t "${IMAGE_NAME}" .

echo "Stopping old container ${CONTAINER_NAME} (if any)..."
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

# Redis port on host (free port for tests); omit REDIS_HOST_PORT to not publish
REDIS_HOST_PORT="${REDIS_HOST_PORT:-63790}"
echo "Starting container ${CONTAINER_NAME} on network ${NETWORK_NAME} (restart=always, user 1000:1000)..."
# Restart policy: always. Bases, configs, logs, models mounted from host. Redis published for tests.
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart=always \
  --network "${NETWORK_NAME}" \
  -p 8015:8015 \
  -p "${REDIS_HOST_PORT}:6379" \
  -u 1000:1000 \
  -v "${CERTS_DIR}:/app/certs:ro" \
  -v "${CONFIG_DIR}:/app/config" \
  -v "${LOGS_DIR}:/app/logs" \
  -v "${CACHE_DIR}:/app/cache" \
  -v "${MODELS_AND_DATA_DIR}:/app/data" \
  -v "${REDIS_DATA_DIR}:/app/redis_data" \
  -e CERTS_DIR=/app/certs \
  -e ADAPTER_PORT=8015 \
  -e ADVERTISED_HOST="${CONTAINER_NAME}" \
  -e OLLAMA_MODELS=/app/data \
  -e OLLAMA_HOME=/app/data \
  -e HOME=/app/data \
  -e OLLAMA_PRELOAD_MODELS="${OLLAMA_PRELOAD_MODELS:-llama3.2,qwen3,qwen2.5-coder:1.5b}" \
  -e OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}" \
  -e OLLAMA_LLM_LIBRARY="${OLLAMA_LLM_LIBRARY:-cpu}" \
  "${IMAGE_NAME}"

echo "Done. Container ${CONTAINER_NAME} is running (adapter 8015, Redis ${REDIS_HOST_PORT}:6379, user 1000:1000, restart=always, network=${NETWORK_NAME})."
echo "Ollama: OLLAMA_LLM_LIBRARY=${OLLAMA_LLM_LIBRARY:-cpu} (CPU-only). Set OLLAMA_LLM_LIBRARY= to use GPU."
echo "Mounts: certs, config, logs, cache, data (models), redis_data (bases)."

echo "Validating runtime contract for ${CONTAINER_NAME}..."
CONTAINER_USER="$(docker inspect -f '{{.Config.User}}' "${CONTAINER_NAME}")"
if [ "${CONTAINER_USER}" != "1000:1000" ]; then
  echo "ERROR: runtime contract violation: user mapping is '${CONTAINER_USER}', expected '1000:1000'."
  exit 1
fi

if ! docker inspect -f '{{if index .NetworkSettings.Networks "smart-assistant"}}ok{{end}}' "${CONTAINER_NAME}" | grep -qx "ok"; then
  echo "ERROR: runtime contract violation: container is not attached to network smart-assistant."
  exit 1
fi

MOUNTS_VIEW="$(docker inspect -f '{{range .Mounts}}{{printf "%s:%s\n" .Source .Destination}}{{end}}' "${CONTAINER_NAME}")"
for required_mount in "/app/config" "/app/logs" "/app/cache" "/app/data"; do
  if ! printf '%s\n' "${MOUNTS_VIEW}" | grep -q ":${required_mount}$"; then
    echo "ERROR: runtime contract violation: required mount ${required_mount} is missing."
    exit 1
  fi
done
echo "Runtime contract validated: mounts, user=1000:1000, network=smart-assistant."

if [ -n "${RUN_SERVER_TESTS}" ]; then
  echo "Running server test pipeline..."
  "${SCRIPT_DIR}/test_server.sh"
fi
