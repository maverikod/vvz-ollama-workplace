# OLLAMA + MCP Proxy Adapter (ollama-workstation) with mTLS
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0

# Install OLLAMA, Python, and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3.12 \
    python3.12-venv \
    python3-pip \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Install OLLAMA
RUN curl -fsSL https://ollama.com/install.sh | sh

# App directory
WORKDIR /app

# Copy project (for ollama_workstation package)
COPY pyproject.toml /app/
COPY src/ /app/src/

# Python venv and deps (no --break-system-packages)
RUN python3.12 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir mcp-proxy-adapter httpx PyYAML && \
    /app/.venv/bin/pip install --no-cache-dir -e /app

# Certificates and config (generated at runtime or mounted)
RUN mkdir -p /app/certs /app/config

# Container scripts
COPY container/entrypoint.sh /app/entrypoint.sh
COPY container/generate_certs.sh /app/generate_certs.sh
COPY container/generate_config.py /app/generate_config.py
COPY container/run_adapter.py /app/run_adapter.py

RUN chmod +x /app/entrypoint.sh /app/generate_certs.sh

# Adapter mTLS port
EXPOSE 8443

ENTRYPOINT ["/app/entrypoint.sh"]
