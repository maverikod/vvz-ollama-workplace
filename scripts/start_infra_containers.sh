#!/bin/sh
# Pull images and start separate Redis + Ollama containers.
# Run from project root: ./scripts/start_infra_containers.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if [ "${PULL_IMAGES:-0}" = "1" ]; then
  echo "Pulling Redis and Ollama images..."
  docker pull "${REDIS_IMAGE:-redis:7-alpine}"
  docker pull "${OLLAMA_IMAGE:-ollama/ollama}"
else
  echo "Skipping docker pull (set PULL_IMAGES=1 to force image refresh)."
fi

echo "Starting Redis container..."
"${SCRIPT_DIR}/start_redis_container.sh"

echo "Starting Ollama container..."
"${SCRIPT_DIR}/start_ollama_container.sh"

echo "Infra is ready: separate containers redis + ollama."
