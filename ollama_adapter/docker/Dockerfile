# Image: ollama-adapter (Ollama + mcp-proxy-adapter server). No Redis.
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com
# Build from ollama_adapter root: docker build -f docker/Dockerfile .

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates zstd python3 python3-venv python3-pip openssl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -e /app

RUN mkdir -p /app/certs /app/config /app/logs /app/data

EXPOSE 8015

# Default: run Ollama then adapter (override with custom entrypoint in run_container.sh if needed).
CMD ["/bin/sh", "-c", "ollama serve & sleep 5 && /app/.venv/bin/python -m ollama_adapter"]
