# MWPS install and verify

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

When using the **MWPS + adapter container**, stop local MWPS and use only the MWPS inside the container. See [container_usage.md](container_usage.md).

## Install (run on your machine)

Install requires `sudo`. Run in a terminal:

```bash
curl -fsSL https://mwps.com/install.sh | sh
```

Or manual (x86_64):

```bash
curl -fsSL https://mwps.com/download/mwps-linux-amd64.tar.zst | sudo tar x -C /usr
```

Then start MWPS (default: serve on `http://127.0.0.1:11434`):

```bash
mwps serve
```

If you get **CUDA out of memory** (e.g. `cudaMalloc failed`) when using Llama or other models, run Model Workplace Server in **CPU-only** mode:

```bash
MWPS_LLM_LIBRARY=cpu mwps serve
```

Or with systemd: create an override (e.g. `sudo systemctl edit mwps`) and set `Environment=MWPS_LLM_LIBRARY=cpu`, then `sudo systemctl restart mwps`.

Or enable systemd service (if the installer created it):

```bash
sudo systemctl enable mwps
sudo systemctl start mwps
```

## Pull a model (for chat and tools)

```bash
mwps pull llama3.2
# or: mwps pull qwen3
```

Use the same name in config as `mwps_model` (e.g. `llama3.2`, `qwen3`).

## Verify

From the project root (with `.venv` activated):

```bash
# 1. Check MWPS is reachable
python scripts/verify_mwps.py

# 2. Optional: quick chat (no tools)
curl -s http://127.0.0.1:11434/api/chat -d '{"model":"llama3.2","messages":[{"role":"user","content":"Say hello in one word."}]}' | head -c 500
```
