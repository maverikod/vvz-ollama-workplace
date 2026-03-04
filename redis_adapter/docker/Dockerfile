# Image: redis-adapter (Redis + mcp-proxy-adapter server).
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com
# Build from redis_adapter root: docker build -f docker/Dockerfile .

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -e /app

RUN mkdir -p /app/certs /app/config /app/logs /app/redis_data

EXPOSE 6379 8016

# Start Redis then adapter server (override with custom entrypoint in run_container.sh if needed).
CMD ["/bin/sh", "-c", "redis-server --dir /app/redis_data & sleep 1 && /app/.venv/bin/python -m redis_adapter"]
