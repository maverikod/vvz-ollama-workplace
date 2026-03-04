# ollama_adapter — Docker

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Scripts to **build the image** and **create/run the container** for the ollama-adapter (Ollama + mcp-proxy-adapter server, SPEC §4).

---

## Scripts

| Script | Purpose |
|--------|---------|
| **build_image.sh** | Build Docker image from ollama_adapter root. |
| **run_container.sh** | Create and start the container (Ollama + adapter) on network `smart-assistant`; mounts config, logs, data (models), certs. |

Run from **subproject root** (`ollama_adapter/`).

---

## Full stack

To run the full stack (redis-adapter, ollama-adapter, model-workspace-server), see root **[docs/container_usage.md](../../docs/container_usage.md)**.
