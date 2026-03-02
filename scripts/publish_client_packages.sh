#!/bin/sh
# Build and publish both client distributions to a PyPI repository using ~/.pypirc.
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

REPOSITORY="${1:-pypi}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"

if [ ! -f "${HOME}/.pypirc" ]; then
  echo "ERROR: ~/.pypirc was not found. Create it before publishing."
  exit 1
fi

if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
  echo "ERROR: .venv was not found in project root."
  exit 1
fi

. "${PROJECT_ROOT}/.venv/bin/activate"

python -m pip show build >/dev/null 2>&1 || python -m pip install build
python -m pip show twine >/dev/null 2>&1 || python -m pip install twine

echo "=== Build: model-workspace-client ==="
rm -rf "${PROJECT_ROOT}/dist/model-workspace-client"
python -m build --sdist --wheel \
  --outdir "${PROJECT_ROOT}/dist/model-workspace-client" \
  "${PROJECT_ROOT}/src/model_workspace_client"

echo "=== Build: ollama-model-database-client ==="
rm -rf "${PROJECT_ROOT}/dist/ollama-model-database-client"
python -m build --sdist --wheel \
  --outdir "${PROJECT_ROOT}/dist/ollama-model-database-client" \
  "${PROJECT_ROOT}/src/database_client"

echo "=== Twine metadata check ==="
twine check \
  "${PROJECT_ROOT}/dist/model-workspace-client/"* \
  "${PROJECT_ROOT}/dist/ollama-model-database-client/"*

UPLOAD_FLAGS=""
if [ "${SKIP_EXISTING}" = "1" ]; then
  UPLOAD_FLAGS="--skip-existing"
fi

echo "=== Upload to repository: ${REPOSITORY} ==="
if [ -n "${UPLOAD_FLAGS}" ]; then
  twine upload --repository "${REPOSITORY}" ${UPLOAD_FLAGS} \
    "${PROJECT_ROOT}/dist/model-workspace-client/"* \
    "${PROJECT_ROOT}/dist/ollama-model-database-client/"*
else
  twine upload --repository "${REPOSITORY}" \
    "${PROJECT_ROOT}/dist/model-workspace-client/"* \
    "${PROJECT_ROOT}/dist/ollama-model-database-client/"*
fi

echo "=== Publish completed ==="
echo "Repository: ${REPOSITORY}"
echo "Artifacts:"
echo "  - dist/model-workspace-client/"
echo "  - dist/ollama-model-database-client/"
