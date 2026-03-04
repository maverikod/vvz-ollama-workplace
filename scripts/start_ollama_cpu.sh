#!/bin/sh
# Start Ollama on the host in CPU-only mode (no GPU). Use for local checks.
# Run from project root: ./scripts/start_ollama_cpu.sh
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e

if command -v ss >/dev/null 2>&1 && ss -tln | grep -q ":11434 "; then
  echo "Port 11434 is in use. Stop existing Ollama first:" >&2
  echo "  sudo systemctl stop ollama   # if using systemd" >&2
  echo "  pkill -f 'ollama serve'       # or kill the process" >&2
  echo "Then run this script again." >&2
  exit 1
fi

export OLLAMA_NUM_GPU="${OLLAMA_NUM_GPU:-0}"
export OLLAMA_LLM_LIBRARY="${OLLAMA_LLM_LIBRARY:-cpu}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-}"
echo "Starting Ollama in CPU-only mode (OLLAMA_NUM_GPU=$OLLAMA_NUM_GPU)..." >&2
exec ollama serve
