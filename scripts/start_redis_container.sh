#!/bin/sh
# Start Redis server in Docker with persistence and restart policy always.
# Run from project root: ./scripts/start_redis_container.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

CONTAINER_NAME="${REDIS_CONTAINER_NAME:-redis}"
IMAGE="${REDIS_IMAGE:-redis:7-alpine}"
PORT="${REDIS_PORT:-6379}"
VOLUME_NAME="${REDIS_VOLUME:-redis-data}"
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
  echo "Redis at 127.0.0.1:${PORT}"
  exit 0
fi

echo "Creating and starting ${CONTAINER_NAME} (${IMAGE}, port ${PORT})..."
if ! docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart always \
  --network "${NETWORK_NAME}" \
  -v "${VOLUME_NAME}:/data" \
  -p "${PORT}:6379" \
  "${IMAGE}" \
  redis-server --appendonly yes; then
  docker rm "${CONTAINER_NAME}" 2>/dev/null || true
  echo "Port ${PORT} may be in use. Try: REDIS_PORT=6380 $0"
  exit 1
fi

echo "Redis container started. Endpoint: redis://${CONTAINER_NAME}:6379 (network ${NETWORK_NAME})"
