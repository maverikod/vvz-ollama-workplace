#!/bin/sh
# Start OLLAMA server in Docker (CPU). Persist models in volume ollama.
# Run from project root: ./scripts/start_ollama_container.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

CONTAINER_NAME="${OLLAMA_CONTAINER_NAME:-ollama}"
IMAGE="${OLLAMA_IMAGE:-ollama/ollama}"
PORT="${OLLAMA_PORT:-11434}"
VOLUME_NAME="${OLLAMA_VOLUME:-ollama}"
NETWORK_NAME="${DOCKER_NETWORK_NAME:-smart-assistant}"

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  echo "Creating docker network ${NETWORK_NAME}..."
  docker network create "${NETWORK_NAME}" >/dev/null
fi

if docker ps -q -f "name=^${CONTAINER_NAME}$" | grep -q .; then
  docker update --restart always "${CONTAINER_NAME}" >/dev/null
  if ! docker inspect -f "{{if index .NetworkSettings.Networks \"${NETWORK_NAME}\"}}ok{{end}}" "${CONTAINER_NAME}" | grep -qx "ok"; then
    docker network connect "${NETWORK_NAME}" "${CONTAINER_NAME}" >/dev/null
  fi
  echo "Container ${CONTAINER_NAME} already running."
  exit 0
fi

if docker ps -aq -f "name=^${CONTAINER_NAME}$" | grep -q .; then
  echo "Starting existing container ${CONTAINER_NAME}..."
  docker update --restart always "${CONTAINER_NAME}" >/dev/null
  if ! docker inspect -f "{{if index .NetworkSettings.Networks \"${NETWORK_NAME}\"}}ok{{end}}" "${CONTAINER_NAME}" | grep -qx "ok"; then
    docker network connect "${NETWORK_NAME}" "${CONTAINER_NAME}" >/dev/null
  fi
  docker start "${CONTAINER_NAME}"
  echo "OLLAMA at http://127.0.0.1:${PORT}"
  exit 0
fi

echo "Creating and starting ${CONTAINER_NAME} (${IMAGE}, port ${PORT}, CPU-only)..."
if ! docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart always \
  --network "${NETWORK_NAME}" \
  -v "${VOLUME_NAME}:/root/.ollama" \
  -p "${PORT}:11434" \
  -e OLLAMA_LLM_LIBRARY="${OLLAMA_LLM_LIBRARY:-cpu}" \
  "${IMAGE}"; then
  docker rm "${CONTAINER_NAME}" 2>/dev/null || true
  echo "Port ${PORT} may be in use (OLLAMA already running?). Try: OLLAMA_PORT=11435 $0"
  exit 1
fi

echo "OLLAMA container started. API: http://127.0.0.1:${PORT}"
echo "Pull a model: docker exec -it ${CONTAINER_NAME} ollama pull llama3.2"
