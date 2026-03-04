#!/bin/sh
# Build Docker image for model-workspace-server.
# Requires repository root as build context (model_workspace depends on ollama_adapter and redis_adapter).
# Run from repository root: ./model_workspace/docker/build_image.sh
# Or from model_workspace/: ./docker/build_image.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBPROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SUBPROJECT_ROOT}/.." && pwd)"

if [ -f "${SCRIPT_DIR}/run.conf" ]; then
  . "${SCRIPT_DIR}/run.conf"
fi
IMAGE_NAME="${IMAGE_NAME:-model-workspace-server}"

echo "Building image ${IMAGE_NAME} from repository root (context: ${REPO_ROOT})..."
docker build -f "${SUBPROJECT_ROOT}/docker/Dockerfile" -t "${IMAGE_NAME}" "${REPO_ROOT}"
echo "Done. Image ${IMAGE_NAME} built."
