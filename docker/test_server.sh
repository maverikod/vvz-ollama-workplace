#!/bin/sh
# Test pipeline for real server: wait for adapter, then JSON-RPC smoke tests.
# Run after ./docker/build_and_run.sh or standalone (container must be running).
# From project root: ./docker/test_server.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if [ -f "${SCRIPT_DIR}/run.conf" ]; then
  . "${SCRIPT_DIR}/run.conf"
fi
CONTAINER_NAME="${CONTAINER_NAME:-ollama-adapter}"

ADAPTER_HOST="${ADAPTER_HOST:-localhost}"
ADAPTER_PORT="${ADAPTER_PORT:-8015}"
ADAPTER_URL="https://${ADAPTER_HOST}:${ADAPTER_PORT}"
WAIT_MAX="${WAIT_MAX:-120}"
CERTS_DIR="${PROJECT_ROOT}/mtls_certificates"
if [ ! -f "${CERTS_DIR}/client.crt" ] || [ ! -f "${CERTS_DIR}/client.key" ]; then
  CERTS_DIR="${PROJECT_ROOT}/docker/certs"
fi

echo "Waiting for server (port ${ADAPTER_PORT}, up to ${WAIT_MAX}s)..."
i=0
while [ $i -lt "$WAIT_MAX" ]; do
  if docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" -q | grep -q .; then
    if curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 2 \
        --cert "${CERTS_DIR}/client.crt" --key "${CERTS_DIR}/client.key" \
        "${ADAPTER_URL}/" 2>/dev/null | grep -q '200\|404\|405'; then
      echo "Server responded on ${ADAPTER_PORT}."
      break
    fi
  fi
  sleep 2
  i=$((i + 2))
done
if [ $i -ge "$WAIT_MAX" ]; then
  echo "Server did not become ready in ${WAIT_MAX}s. Logs:"
  docker logs "${CONTAINER_NAME}" 2>&1 | tail -30
  exit 1
fi

echo "Server smoke tests (JSON-RPC)..."
BODY='{"jsonrpc":"2.0","method":"server_status","params":{},"id":1}'
RESP=$(curl -k -s -X POST \
  --cert "${CERTS_DIR}/client.crt" --key "${CERTS_DIR}/client.key" \
  -H "Content-Type: application/json" \
  -d "${BODY}" \
  "${ADAPTER_URL}/" 2>/dev/null || echo "{}")
if echo "${RESP}" | grep -q '"result"'; then
  echo "server_status: OK"
else
  echo "server_status failed. Response: ${RESP}"
  exit 1
fi

BODY2='{"jsonrpc":"2.0","method":"session_init","params":{},"id":2}'
RESP2=$(curl -k -s -X POST \
  --cert "${CERTS_DIR}/client.crt" --key "${CERTS_DIR}/client.key" \
  -H "Content-Type: application/json" \
  -d "${BODY2}" \
  "${ADAPTER_URL}/" 2>/dev/null || echo "{}")
if echo "${RESP2}" | grep -q '"result"'; then
  echo "session_init: OK"
else
  echo "session_init response: ${RESP2}"
fi

echo "Server test pipeline OK."
