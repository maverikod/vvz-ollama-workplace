#!/bin/sh
# Build Docker image for ollama-adapter (Ollama + adapter server).
# Run from subproject root: ./docker/build_image.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBPROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${SCRIPT_DIR}/run.conf" ]; then
  . "${SCRIPT_DIR}/run.conf"
fi
IMAGE_NAME="${IMAGE_NAME:-ollama-adapter}"

echo "Building image ${IMAGE_NAME}..."
docker build -f "${SUBPROJECT_ROOT}/docker/Dockerfile" -t "${IMAGE_NAME}" "${SUBPROJECT_ROOT}"
echo "Done. Image ${IMAGE_NAME} built."
