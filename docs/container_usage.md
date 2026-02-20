# OLLAMA + Redis + Adapter container

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

The image includes **Redis** and the **project server** (OLLAMA + MCP adapter). Bases, configs, logs, and models are **mounted from the host**. The run script uses user **1000:1000**, **restart=always**, and connects the container to the **smart-assistant** network.

## Use OLLAMA only from the container

When running the OLLAMA + adapter stack in Docker, **stop the local OLLAMA** so that only the container’s OLLAMA is used (the adapter inside the container talks to `http://127.0.0.1:11434`).

Stop local OLLAMA:

```bash
# If running as a service
sudo systemctl stop ollama

# If started manually, find and stop the process
pkill -f "ollama serve"
# or: kill $(pgrep -f "ollama serve")
```

Then run the container; OLLAMA will start inside the container and the adapter will use it.

If **ollama_chat** returns 404, the requested model is usually not pulled. Either pull it once (e.g. `docker exec <container> ollama pull llama3.2`) or set `OLLAMA_PULL_MODEL=1` when running the container so the default model is pulled on first start (slow on first run).

## Auto-registration with MCP proxy

The adapter is configured with `registration.enabled: true` and `auto_on_startup: true`. On startup, the adapter’s lifespan:

1. Registers with the proxy at `https://mcp-proxy:3004` (mTLS) using the generated config.
2. Starts the heartbeat task so the proxy keeps the server in the catalog.

No extra steps are needed: start the container and ensure the proxy is reachable at `mcp-proxy:3004` on the same Docker network (or set `MCP_PROXY_HOST` / `MCP_PROXY_PORT`).

## Build and run (recommended: script in `docker/`)

From the project root:

```bash
./docker/build_and_run.sh
```

The script builds the image from `docker/Dockerfile`, stops the old container, runs a new one with **restart=always** on network **smart-assistant** with user **1000:1000**, and mounts: **config**, **logs**, **cache**, **data** (OLLAMA models), **redis_data** (Redis persistence), **certs**. Override via env: `NETWORK_NAME=smart-assistant` (default), `IMAGE_NAME`, `CONTAINER_NAME`.

**Server test pipeline (in project):** After the container is running, run `./docker/test_server.sh` to wait for the adapter and run JSON-RPC smoke tests (server_status, session_init). To run this automatically after build and run, use `RUN_SERVER_TESTS=1 ./docker/build_and_run.sh`. Full pipeline from root (unit tests → build → run → server tests): `./scripts/build_run_and_test_server.sh` (uses `docker/build_and_run.sh` and `docker/test_server.sh`).

To use an existing MCP proxy on another container, put both on the same network and set the proxy host (e.g. service name):

```bash
docker network create ollama-net
docker run -d --name mcp-proxy --network ollama-net -p 3004:3004 your-mcp-proxy-image
docker run --rm --network ollama-net -p 8443:8443 -e MCP_PROXY_HOST=mcp-proxy ollama-adapter
```

Ensure the MCP proxy is on the **smart-assistant** network and reachable at `mcp-proxy:3004` (or set `MCP_PROXY_HOST` / `MCP_PROXY_PORT`). The adapter registers at `https://mcp-proxy:3004` (mTLS). The proxy will not accept the connection without the correct client certificate.

## mTLS certificates (so the proxy accepts the adapter)

The proxy uses mTLS and only accepts clients with a certificate it trusts. Use the **mtls_certificates** folder:

1. **Generate certs** (CN = container name from `docker/run.conf`, e.g. `ollama-adapter`):
   ```bash
   ./mtls_certificates/generate_certs.sh
   ```
2. **Configure the proxy** to trust this CA: add `mtls_certificates/ca.crt` to the proxy’s trusted CAs for client verification.
3. **Run the container**: `./docker/build_and_run.sh` will use `mtls_certificates/` as `/app/certs` when all of `ca.crt`, `client.crt`, `client.key`, `server.crt`, `server.key` are present. The adapter will then connect to the proxy with `client.crt` and the proxy will accept it.

If you use the proxy’s own CA, put it as `mtls_certificates/ca.crt` and generate server/client certs signed by that CA with CN = container name; see `mtls_certificates/README.md`.

**Troubleshooting:** If you see "Proxy not available at https://mcp-proxy:3004", see [registration_troubleshooting.md](registration_troubleshooting.md).
