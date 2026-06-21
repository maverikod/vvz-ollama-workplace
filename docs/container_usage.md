# Stack: OLLAMA + Redis + Adapter containers

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes running the **full stack** per [SPEC §4](plans/refactoring_adapter_structure/SPEC.md): containers **redis-adapter** (Redis + adapter server), **ollama-adapter** (Ollama + adapter server), and **model-workspace-server** (model workspace app only). The model workspace has **no** Redis or Ollama inside; it uses **clients** to redis-adapter and ollama-adapter (WebSocket via proxy).

**Legacy / single image:** Some setups use one image that includes Redis, OLLAMA, and the project server (MCP adapter). Bases, configs, logs, and models are mounted from the host. The run script uses user **1000:1000**, **restart=always**, and connects the container to the **smart-assistant** network.

## Use OLLAMA only from the stack

When running the OLLAMA + adapter stack in Docker, **stop the local OLLAMA** so that only the stack’s OLLAMA is used (the adapter inside the container talks to `http://127.0.0.1:11434` or to the ollama_adapter service).

Stop local OLLAMA:

```bash
# If running as a service
sudo systemctl stop ollama

# If started manually
pkill -f "ollama serve"
```

Then run the container(s); OLLAMA will start inside the stack and the adapter will use it.

If **ollama_chat** returns 404, the requested model is usually not pulled. Either pull it once (e.g. `docker exec <container> ollama pull llama3.2`) or set `OLLAMA_PULL_MODEL=1` when running the container so the default model is pulled on first start (slow on first run).

**Empty message or timeout:** If the model reply is empty or the request stops after ~60s, increase `ollama_timeout` in the workstation config (e.g. 120). Cold model or long context can exceed 60s. In container logs, a `500` on `POST /api/chat` after ~1m usually means OLLAMA hit an internal timeout or error; retry or increase timeouts.

**SERVER_UNAVAILABLE from proxy:** Often means the adapter raised an error before returning. Check adapter logs (`docker logs <container>`). If you see `Command timed out after 120.00s` (or similar), the command (e.g. `ollama_chat`) exceeded the adapter’s execution timeout. Increase the command timeout in the adapter config (e.g. 300) and restart the container; also ensure `ollama_timeout` is high enough for slow or cold model responses.

**No cold start:** The adapter may run model loading and **warm-up** (pull missing models, then one minimal chat per model) **before** starting the HTTP server. So the first `ollama_chat` is served when the model is already loaded.

**Keep model in memory:** The entrypoint may set `OLLAMA_KEEP_ALIVE=-1` by default (never unload). Override with env when running (e.g. `-e OLLAMA_KEEP_ALIVE=30m` for 30 minutes idle).

## Auto-registration with MCP proxy

The adapter is configured with `registration.enabled: true` and `auto_on_startup: true`. On startup, the adapter’s lifespan:

1. Registers with the proxy at `https://mcp-proxy:3004` (mTLS) using the generated config.
2. Starts the heartbeat task so the proxy keeps the server in the catalog.

No extra steps are needed: start the container and ensure the proxy is reachable at `mcp-proxy:3004` on the same Docker network (or set `MCP_PROXY_HOST` / `MCP_PROXY_PORT`).

## Build and run: per-subproject `docker/`

Each subproject has its own **docker/** with scripts to form the image and create the container:

| Subproject       | Build image              | Run container              | Container name           |
|------------------|--------------------------|----------------------------|--------------------------|
| **redis_adapter**   | `./docker/build_image.sh` (from redis_adapter/)   | `./docker/run_container.sh` | redis-adapter            |
| **ollama_adapter**  | `./docker/build_image.sh` (from ollama_adapter/)  | `./docker/run_container.sh` | ollama-adapter            |
| **model_workspace** | `./model_workspace/docker/build_image.sh` (from repo root) | `./model_workspace/docker/run_container.sh` | model-workspace-server |

**Full stack order:** Create network `smart-assistant`, then build and run: 1) redis-adapter, 2) ollama-adapter, 3) model-workspace-server. Each script mounts config, logs, certs (from repo `mtls_certificates/` when present). See each subproject’s **docker/README.md**.

**Legacy (single image):** From the project root, `./docker/build_and_run.sh` still builds one image (Redis + OLLAMA + adapter) for backward compatibility. Prefer the per-subproject scripts above for the target three-container layout (SPEC §4).

To use an existing MCP proxy on another container, put both on the same network and set the proxy host (e.g. service name):

```bash
docker network create ollama-net
docker run -d --name mcp-proxy --network ollama-net -p 3004:3004 your-mcp-proxy-image
docker run --rm --network ollama-net -p 8443:8443 -e MCP_PROXY_HOST=mcp-proxy ollama-adapter
```

Ensure the MCP proxy is on the **smart-assistant** network and reachable at `mcp-proxy:3004` (or set `MCP_PROXY_HOST` / `MCP_PROXY_PORT`). The adapter registers at `https://mcp-proxy:3004` (mTLS). The proxy will not accept the connection without the correct client certificate.

## mTLS certificates (so the proxy accepts the adapter)

The proxy uses mTLS and only accepts clients with a certificate it trusts. Use the **mtls_certificates** folder (in repository root):

1. **Generate certs** (CN = container name from `docker/run.conf`, e.g. `ollama-adapter`):
   ```bash
   ./mtls_certificates/generate_certs.sh
   ```
2. **Configure the proxy** to trust this CA: add `mtls_certificates/ca.crt` to the proxy’s trusted CAs for client verification.
3. **Run the container**: `./docker/build_and_run.sh` will use `mtls_certificates/` as `/app/certs` when all of `ca.crt`, `client.crt`, `client.key`, `server.crt`, `server.key` are present. The adapter will then connect to the proxy with `client.crt` and the proxy will accept it.

If you use the proxy’s own CA, put it as `mtls_certificates/ca.crt` and generate server/client certs signed by that CA with CN = container name; see `mtls_certificates/README.md`.

**Troubleshooting:** If you see "Proxy not available at https://mcp-proxy:3004", see [registration_troubleshooting.md](registration_troubleshooting.md).

## Test container (code mounted, no rebuild)

A **test** container with name suffix `-test` (e.g. `ollama-adapter-test`) uses the **same image** but mounts project code from the host so you can change code without rebuilding the image.

**Run (from project root):**

```bash
./docker/run_test_container.sh
```

**Requirements:** The image must exist (run `./docker/build_and_run.sh` at least once).

**Behaviour:**

- Container name: `ollama-adapter-test` (set in `docker/run.conf` as `CONTAINER_NAME_TEST`).
- Ports on host: adapter **8016**, Redis **63791** (so it can run alongside the main container on 8015/63790).
- Mounts (read-only): `src/`, `scripts/`, `pyproject.toml` from the project; config, logs, data, redis_data are the same dirs as for the main container (or separate if you change paths).
- No `restart=always`; after code changes, restart with: `docker restart ollama-adapter-test`.

To run the Redis verification pipeline against the test container’s Redis: `REDIS_PORT=63791 ./scripts/run_verify_pipeline.sh` (or `verify_redis_pipeline.py`).

## Commercial models (cheapest options)

For Google, Anthropic, and OpenAI the project defines the **cheapest** (lowest-cost) model id per provider. Set the corresponding API key and use these model ids in config or in session:

| Provider   | Cheapest model id              | Config key          |
|-----------|--------------------------------|---------------------|
| Google    | `gemini-2.0-flash`             | `google_api_key`    |
| Anthropic | `claude-3-5-haiku-20241022`    | `anthropic_api_key` |
| OpenAI    | `gpt-4o-mini`                  | `openai_api_key`    |
| xAI Grok  | `grok-2`                       | `xai_api_key`      |
| DeepSeek  | `deepseek-chat`                | `deepseek_api_key`  |

In config set `available_providers` (e.g. `["ollama", "google"]`) and the required key; use the model id in sessions or as default model.

## Local config with API keys (gitignored)

To keep API keys out of the repo, use a **local** config file that is gitignored:

1. **Copy the example** (same structure as main config, with placeholder keys):
   ```bash
   cp config/adapter_config.local.json.example config/adapter_config.local.json
   ```
2. **Edit** `config/adapter_config.local.json`: replace placeholders with your real keys.
3. **Run** with that config:
   ```bash
   export ADAPTER_CONFIG_PATH=config/adapter_config.local.json
   # then start the adapter / container as usual
   ```
   In Docker, pass the path when generating or mounting config so the container receives config from a volume that contains your `adapter_config.local.json`.

The file **`config/adapter_config.local.json`** is listed in `.gitignore` and must **never** be committed. Only the example with placeholders is in the repo.
