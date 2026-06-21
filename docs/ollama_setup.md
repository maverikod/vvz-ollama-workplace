# OLLAMA install and verify

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

When using the **OLLAMA + adapter container**, stop local OLLAMA and use only the OLLAMA inside the container. See [container_usage.md](container_usage.md).

## Install (run on your machine)

Install requires `sudo`. Run in a terminal:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or manual (x86_64):

```bash
curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | sudo tar x -C /usr
```

Then start OLLAMA (default: serve on `http://127.0.0.1:11434`):

```bash
ollama serve
```

If you get **CUDA out of memory** (e.g. `cudaMalloc failed`) when using Llama or other models, run Ollama in **CPU-only** mode:

```bash
OLLAMA_LLM_LIBRARY=cpu ollama serve
```

Or with systemd: create an override (e.g. `sudo systemctl edit ollama`) and set `Environment=OLLAMA_LLM_LIBRARY=cpu`, then `sudo systemctl restart ollama`.

Or enable systemd service (if the installer created it):

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

## Pull a model (for chat and tools)

```bash
ollama pull llama3.2
# or: ollama pull qwen3
```

Use the same name in config as `ollama_model` (e.g. `llama3.2`, `qwen3`).

## Verify

From the project root (with `.venv` activated):

```bash
# 1. Check OLLAMA is reachable
python scripts/verify_ollama.py

# 2. Optional: quick chat (no tools)
curl -s http://127.0.0.1:11434/api/chat -d '{"model":"llama3.2","messages":[{"role":"user","content":"Say hello in one word."}]}' | head -c 500
```
