# model_workspace — Docker

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Scripts to **build the image** and **create/run the container** for the model-workspace-server (SPEC §4). This subproject has no Redis or Model Workplace Server inside; it uses clients to redis-adapter and mwps-adapter.

---

## Scripts

| Script | Purpose |
|--------|---------|
| **build_image.sh** | Build Docker image from repository root (needs mwps_adapter and redis_adapter in repo). |
| **run_container.sh** | Create and start the container on network `smart-assistant`; mounts config, logs, certs. |

Run from **subproject root** (`model_workspace/`) or from **repository root** as indicated in each script.

---

## Full stack

To run the full stack (redis-adapter, mwps-adapter, model-workspace-server), see root **[docs/container_usage.md](../../docs/container_usage.md)**.
