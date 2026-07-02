# Image: model-workspace-server (application only; no Redis or Model Workplace Server inside).
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com
# Build from repo root: docker build -f model_workspace/docker/Dockerfile .

FROM python:3.12-slim

WORKDIR /app

# Copy subprojects (model_workspace depends on provider client packages).
COPY model_workspace/           /app/model_workspace/
COPY mwps_provider_client/    /app/mwps_provider_client/
COPY redis_provider_client/     /app/redis_provider_client/

# Install provider clients then model_workspace (editable).
RUN pip install --no-cache-dir -e /app/redis_provider_client -e /app/mwps_provider_client && \
    pip install --no-cache-dir -e /app/model_workspace

RUN mkdir -p /app/config /app/logs /app/certs

EXPOSE 8017

# Default: run the workspace app (override in run_container.sh if entrypoint differs).
CMD ["python", "-m", "model_workspace"]
