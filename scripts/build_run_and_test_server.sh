#!/bin/sh
# Full pipeline: unit tests -> build and run container (docker/) -> server smoke tests (docker/).
# Uses existing docker/build_and_run.sh and docker/test_server.sh.
# Run from project root: ./scripts/build_run_and_test_server.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=== 1. Unit tests ==="
. "${PROJECT_ROOT}/.venv/bin/activate"
pytest tests/unit -v --tb=short
echo ""

echo "=== 2. Build image and run container ==="
"${PROJECT_ROOT}/docker/build_and_run.sh"
echo ""

echo "=== 3. Server test pipeline ==="
"${PROJECT_ROOT}/docker/test_server.sh"
echo ""

echo "=== Pipeline OK ==="
