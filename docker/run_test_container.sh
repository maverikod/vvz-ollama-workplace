#!/bin/sh
# Run test container (suffix -test): same image, project code mounted so no rebuild needed.
# Run from project root: ./docker/run_test_container.sh
# Requires: image built at least once (e.g. ./docker/build_and_run.sh).
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if [ -f "${SCRIPT_DIR}/run.conf" ]; then
  . "${SCRIPT_DIR}/run.conf"
fi
IMAGE_NAME="${IMAGE_NAME:-ollama-adapter}"
CONTAINER_NAME_TEST="${CONTAINER_NAME_TEST:-ollama-adapter-test}"
NETWORK_NAME="${NETWORK_NAME:-smart-assistant}"
TEST_ADAPTER_HOST_PORT="${TEST_ADAPTER_HOST_PORT:-8016}"
TEST_REDIS_HOST_PORT="${TEST_REDIS_HOST_PORT:-63791}"

CONFIG_DIR="${SCRIPT_DIR}/config"
LOGS_DIR="${SCRIPT_DIR}/logs"
CACHE_DIR="${SCRIPT_DIR}/cache"
DATA_DIR="${SCRIPT_DIR}/data"
REDIS_DATA_DIR="${SCRIPT_DIR}/redis_data"
CERTS_DIR="${SCRIPT_DIR}/certs"
MTLS_DIR="${PROJECT_ROOT}/mtls_certificates"
if [ -f "${MTLS_DIR}/ca.crt" ] && [ -f "${MTLS_DIR}/client.crt" ] && [ -f "${MTLS_DIR}/client.key" ] && [ -f "${MTLS_DIR}/server.crt" ] && [ -f "${MTLS_DIR}/server.key" ]; then
  CERTS_DIR="${MTLS_DIR}"
  echo "Using certs from mtls_certificates/ (proxy-trusted)."
fi

for d in "${CONFIG_DIR}" "${LOGS_DIR}" "${CACHE_DIR}" "${DATA_DIR}" "${REDIS_DATA_DIR}" "${SCRIPT_DIR}/certs"; do
  mkdir -p "$d"
done

echo "Stopping old test container ${CONTAINER_NAME_TEST} (if any)..."
docker stop "${CONTAINER_NAME_TEST}" 2>/dev/null || true
docker rm "${CONTAINER_NAME_TEST}" 2>/dev/null || true

echo "Starting test container ${CONTAINER_NAME_TEST} (code mounted, no rebuild needed)..."
# Same image; mount project code so changes are visible without rebuild.
docker run -d \
  --name "${CONTAINER_NAME_TEST}" \
  --network "${NETWORK_NAME}" \
  -p "${TEST_ADAPTER_HOST_PORT}:8015" \
  -p "${TEST_REDIS_HOST_PORT}:6379" \
  -u 1000:1000 \
  -v "${PROJECT_ROOT}/src:/app/src:ro" \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:ro" \
  -v "${PROJECT_ROOT}/pyproject.toml:/app/pyproject.toml:ro" \
  -v "${SCRIPT_DIR}/run_adapter.py:/app/run_adapter.py:ro" \
  -v "${CERTS_DIR}:/app/certs:ro" \
  -v "${CONFIG_DIR}:/app/config" \
  -v "${LOGS_DIR}:/app/logs" \
  -v "${CACHE_DIR}:/app/cache" \
  -v "${DATA_DIR}:/app/data" \
  -v "${REDIS_DATA_DIR}:/app/redis_data" \
  -e CERTS_DIR=/app/certs \
  -e ADAPTER_PORT=8015 \
  -e ADVERTISED_HOST="${CONTAINER_NAME_TEST}" \
  -e OLLAMA_MODELS=/app/data \
  -e OLLAMA_HOME=/app/data \
  -e HOME=/app/data \
  -e OLLAMA_PRELOAD_MODELS="${OLLAMA_PRELOAD_MODELS:-llama3.2,qwen3,qwen2.5-coder:1.5b}" \
  -e OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}" \
  "${IMAGE_NAME}"

echo "Done. Test container ${CONTAINER_NAME_TEST} is running."
echo "  Adapter: host ${TEST_ADAPTER_HOST_PORT} -> 8015, Redis: host ${TEST_REDIS_HOST_PORT} -> 6379."
echo "  Mounts: /app/src, /app/scripts, pyproject.toml from project (read-only); config, logs, data, redis_data."
echo "  No restart policy; code changes take effect after container restart (docker restart ${CONTAINER_NAME_TEST})."
