#!/usr/bin/env python3
"""
Final release gate: real WS E2E for model-workspace and database flows.

Runs mandatory WS path verification (integration tests) and a negative TLS
scenario. Exits 0 only when real WS E2E is healthy; blocks release on any
failure. See docs/plans/refactoring_container_split/atomic_v2/step_18_*.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
import ssl
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_TEST_PATH = (
    PROJECT_ROOT / "tests" / "integration" / "test_proxy_and_servers.py"
)


def _run_integration_tests() -> tuple[bool, str]:
    """
    Run integration tests (real proxy, model-workspace + database contracts).

    Returns (success, message). Success is True only when pytest exits 0.
    """
    if not INTEGRATION_TEST_PATH.is_file():
        return False, "Integration test file not found: %s" % INTEGRATION_TEST_PATH
    env = os.environ.copy()
    # Prefer project venv for pytest
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.is_file():
        cmd = [
            str(venv_python),
            "-m",
            "pytest",
            str(INTEGRATION_TEST_PATH),
            "-m",
            "integration",
            "-v",
            "--tb=short",
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(INTEGRATION_TEST_PATH),
            "-m",
            "integration",
            "-v",
            "--tb=short",
        ]
    result = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True, timeout=120
    )
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        return False, "Integration tests failed (exit %s): %s" % (
            result.returncode,
            result.stderr or result.stdout,
        )
    # Release gate requires real topology; no skipped tests
    if "skipped" in out.lower():
        return (
            False,
            "Integration tests had skips (gate requires real topology, no skips)",
        )
    return True, "Integration tests passed"


def _negative_tls_rejected(
    proxy_base_url: str, timeout_seconds: int = 10
) -> tuple[bool, str]:
    """
    Verify that proxy rejects connections without valid mTLS (negative TLS scenario).

    Attempts HTTPS request to proxy without client cert (or with default context).
    We expect SSL handshake failure or connection error. If the server accepts
    the connection and returns HTTP 200, that is a security failure.

    Returns (success, message). Success is True when bad TLS is rejected.
    """
    if not proxy_base_url or not proxy_base_url.strip():
        return False, "Proxy URL not set (MCP_PROXY_URL or adapter config)"
    url = proxy_base_url.strip().rstrip("/")
    if not url.startswith("https://"):
        return False, "Negative TLS check only applies to https proxy: %s" % url
    try:
        # Context without client cert: server requiring mTLS should reject
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url + "/list", method="GET")
        urllib.request.urlopen(req, timeout=timeout_seconds, context=ctx)
        # If we get here, server accepted connection without valid client cert
        return (
            False,
            "Security: proxy accepted connection without valid mTLS client cert",
        )
    except ssl.SSLError:
        # Expected: handshake failure when client has no/wrong cert
        return (
            True,
            "Negative TLS OK: proxy rejected connection (SSL error as expected)",
        )
    except OSError as e:
        # Connection refused/timeout: cannot confirm TLS rejection; fail gate
        return False, "Negative TLS inconclusive (connection failed): %s" % e
    except Exception as e:
        return False, "Negative TLS check failed: %s" % e


def _get_proxy_base_url() -> str:
    """Get proxy base URL from ADAPTER_CONFIG_PATH or MCP_PROXY_URL."""
    path = os.environ.get("ADAPTER_CONFIG_PATH", "")
    if path and Path(path).exists():
        try:
            src_dir = str(PROJECT_ROOT / "src")
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from ollama_workstation.config import load_config  # noqa: E402

            cfg = load_config(path)
            return (getattr(cfg, "mcp_proxy_url", "") or "").strip().rstrip("/")
        except Exception:
            pass
    return (os.environ.get("MCP_PROXY_URL", "") or "").strip().rstrip("/")


def main() -> int:
    """Run final real WS gate; exit 0 only when all checks pass."""
    print("=== Final Real WS E2E Gate ===")
    failures = 0

    # 1. Mandatory WS path verification (model-workspace + database flows)
    print("\n1. Integration tests (real proxy, model-workspace + database contracts)")
    ok, msg = _run_integration_tests()
    if not ok:
        print("  FAIL: %s" % msg)
        failures += 1
    else:
        print("  OK: %s" % msg)

    # 2. Negative TLS scenario
    print("\n2. Negative TLS scenario (proxy must reject invalid/no mTLS)")
    proxy_url = _get_proxy_base_url()
    ok, msg = _negative_tls_rejected(proxy_url)
    if not ok:
        print("  FAIL: %s" % msg)
        failures += 1
    else:
        print("  OK: %s" % msg)

    if failures:
        print("\nGate FAILED (%s requirement(s) failed). Block release." % failures)
        return 1
    print("\nGate PASSED. Real WS E2E healthy for model-workspace and database flows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
