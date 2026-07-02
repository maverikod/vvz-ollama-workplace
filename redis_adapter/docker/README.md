# redis_adapter — Docker

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Scripts to **build the image** and **create/run the container** for the redis-adapter (Redis + mcp-proxy-adapter server, SPEC §4).

---

## Scripts

| Script | Purpose |
|--------|---------|
| **build_image.sh** | Build Docker image from redis_adapter root. |
| **run_container.sh** | Create and start the container (Redis + adapter) on network `smart-assistant`; mounts config, logs, redis_data, certs. |

Run from **subproject root** (`redis_adapter/`).

---

## Full stack

To run the full stack (redis-adapter, mwps-adapter, model-workspace-server), see root **[docs/container_usage.md](../../docs/container_usage.md)**.
