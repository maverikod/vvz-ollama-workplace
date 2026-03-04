# Image: model-workspace-server (application only; no Redis or Ollama inside).
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com
# Build from repo root: docker build -f model_workspace/docker/Dockerfile .

FROM python:3.12-slim

WORKDIR /app

# Copy subprojects (model_workspace depends on ollama_adapter and redis_adapter).
COPY model_workspace/ /app/model_workspace/
COPY ollama_adapter/   /app/ollama_adapter/
COPY redis_adapter/   /app/redis_adapter/

# Install adapters then model_workspace (editable).
RUN pip install --no-cache-dir -e /app/redis_adapter -e /app/ollama_adapter && \
    pip install --no-cache-dir -e /app/model_workspace

RUN mkdir -p /app/config /app/logs /app/certs

EXPOSE 8017

# Default: run the workspace app (override in run_container.sh if entrypoint differs).
CMD ["python", "-m", "model_workspace"]
