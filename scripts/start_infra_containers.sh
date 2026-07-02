#!/bin/sh
# Pull images and start Redis container (no Model Workplace Server container).
# Run from project root: ./scripts/start_infra_containers.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if [ "${PULL_IMAGES:-0}" = "1" ]; then
  echo "Pulling Redis image..."
  docker pull "${REDIS_IMAGE:-redis:7-alpine}"
else
  echo "Skipping docker pull (set PULL_IMAGES=1 to force image refresh)."
fi

echo "Starting Redis container..."
"${SCRIPT_DIR}/start_redis_container.sh"

echo "Infra is ready: Redis container. Model Workplace Server is provided by mwps-adapter container."
