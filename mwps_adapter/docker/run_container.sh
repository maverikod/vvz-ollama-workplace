#!/bin/sh
# Create and start container mwps-adapter on network smart-assistant.
# Run from mwps_adapter/: ./docker/run_container.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBPROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

. "${SCRIPT_DIR}/run.conf"
NETWORK_NAME="${NETWORK_NAME:-smart-assistant}"

CONFIG_DIR="${SCRIPT_DIR}/config"
LOGS_DIR="${SCRIPT_DIR}/logs"
DATA_DIR="${SCRIPT_DIR}/data"
REPO_ROOT="$(cd "${SUBPROJECT_ROOT}/.." && pwd)"
CERTS_DIR="${REPO_ROOT}/mtls_certificates"
if [ ! -f "${CERTS_DIR}/ca.crt" ] || [ ! -f "${CERTS_DIR}/client.crt" ]; then
  CERTS_DIR="${SCRIPT_DIR}/certs"
fi

mkdir -p "${CONFIG_DIR}" "${LOGS_DIR}" "${DATA_DIR}" "${SCRIPT_DIR}/certs"

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  echo "Creating docker network ${NETWORK_NAME}..."
  docker network create "${NETWORK_NAME}" >/dev/null
fi

echo "Stopping old container ${CONTAINER_NAME} (if any)..."
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

ADAPTER_HOST_PORT="${ADAPTER_HOST_PORT:-8015}"

echo "Starting container ${CONTAINER_NAME} on network ${NETWORK_NAME}..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart=unless-stopped \
  --network "${NETWORK_NAME}" \
  -p "${ADAPTER_HOST_PORT}:8015" \
  -u 1000:1000 \
  -v "${CERTS_DIR}:/app/certs:ro" \
  -v "${CONFIG_DIR}:/app/config" \
  -v "${LOGS_DIR}:/app/logs" \
  -v "${DATA_DIR}:/app/data" \
  -e MWPS_MODELS=/app/data \
  -e MWPS_HOME=/app/data \
  -e MWPS_KEEP_ALIVE="${MWPS_KEEP_ALIVE:--1}" \
  -e MWPS_LLM_LIBRARY="${MWPS_LLM_LIBRARY:-}" \
  "${IMAGE_NAME}"

echo "Done. Container ${CONTAINER_NAME} is running (adapter ${ADAPTER_HOST_PORT}:8015, network=${NETWORK_NAME})."
