"""
Ensure model server (Ollama) Docker container is running: start if stopped,
create from image if missing.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# Default port exposed by Ollama in container
DEFAULT_OLLAMA_PORT = 11434


def ensure_model_server_container(
    container_name: str,
    image: str,
    host_port: int = DEFAULT_OLLAMA_PORT,
    container_port: int = DEFAULT_OLLAMA_PORT,
) -> bool:
    """
    Ensure the model server container exists and is running.
    If container exists but is stopped, start it.
    If container does not exist, create it from image with port mapping.

    Returns True if container is running (or was started/created), False on failure.
    """
    if not container_name.strip() or not image.strip():
        logger.warning(
            "ensure_model_server_container: container_name and image required"
        )
        return False
    name = container_name.strip()
    img = image.strip()
    try:
        # List containers matching name (filter is substring; we need exact match)
        out = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        existing_status: Optional[str] = None
        for line in (out.stdout or "").strip().splitlines():
            parts = line.split("\t", 1)
            if parts and parts[0].strip() == name:
                existing_status = (parts[1] if len(parts) > 1 else "").lower()
                break
        if existing_status and existing_status.startswith("up"):
            logger.info("Model server container %s already running", name)
            return True
        if existing_status:
            # Exists but stopped
            logger.info("Starting existing model server container %s", name)
            r = subprocess.run(
                ["docker", "start", name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            if r.returncode == 0:
                logger.info("Model server container %s started", name)
                return True
            logger.warning("Model server container %s failed to start", name)
            return False
        # Container does not exist: create from image
        logger.info("Creating model server container %s from image %s", name, img)
        run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "%s:%s" % (host_port, container_port),
            img,
        ]
        subprocess.run(run_cmd, capture_output=True, timeout=120, check=False)
        out3 = subprocess.run(
            ["docker", "ps", "--filter", "name=^%s$" % name, "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if (out3.stdout or "").strip():
            logger.info("Model server container %s created and running", name)
            return True
        logger.warning("Model server container %s create failed", name)
        return False
    except FileNotFoundError:
        logger.warning("docker not found; skip container ensure")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("ensure_model_server_container timeout for %s", name)
        return False
    except Exception as e:
        logger.warning("ensure_model_server_container error: %s", e)
        return False
