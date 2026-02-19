# OLLAMA + MCP Proxy Adapter (ollama-workstation) with mTLS
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com
# Build from project root: docker build -f docker/Dockerfile .

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    zstd \
    python3 \
    python3-venv \
    python3-pip \
    openssl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir mcp-proxy-adapter httpx PyYAML && \
    /app/.venv/bin/pip install --no-cache-dir -e /app

RUN mkdir -p /app/certs /app/config /app/logs /app/data /app/cache

COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/ensure_ollama_models.py /app/ensure_ollama_models.py
COPY docker/generate_config.py /app/generate_config.py
COPY docker/run_adapter.py /app/run_adapter.py

RUN chmod +x /app/entrypoint.sh

EXPOSE 8015

ENTRYPOINT ["/app/entrypoint.sh"]
