"""
Unit tests for docker/ensure_ollama_models: model loading (mocked subprocess).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "docker"))


def _ollama_list_output(model_names: list[str]) -> str:
    """Build stdout like 'ollama list' (header + one column name per line)."""
    lines = ["NAME    ID    SIZE    MODIFIED"]
    for name in model_names:
        lines.append(f"{name}    abc123    1.2GB    now")
    return "\n".join(lines) + "\n"


def test_config_missing_returns_zero_no_pull(tmp_path: Path) -> None:
    """Config missing: main returns 0 and does not call ollama."""
    env = {"ADAPTER_CONFIG_PATH": str(tmp_path / "missing.json")}
    with patch.dict(os.environ, env, clear=False):
        with patch("subprocess.run") as mock_run:
            import ensure_ollama_models as mod  # noqa: E402

            import importlib

            importlib.reload(mod)
            exit_code = mod.main()
    assert exit_code == 0
    mock_run.assert_not_called()


def test_all_models_present_skips_pull(tmp_path: Path) -> None:
    """When all config models are already listed, no pull is run."""
    config_path = tmp_path / "adapter_config.json"
    config_path.write_text(
        json.dumps(
            {
                "ollama_workstation": {"ollama_models": ["llama3.2", "qwen3"]},
            }
        ),
        encoding="utf-8",
    )
    env = {"ADAPTER_CONFIG_PATH": str(config_path)}
    list_stdout = _ollama_list_output(["llama3.2", "qwen3"])

    with patch.dict(os.environ, env, clear=False):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=list_stdout, stderr=""
            )
            import ensure_ollama_models as mod  # noqa: E402

            import importlib

            importlib.reload(mod)
            exit_code = mod.main()
    assert exit_code == 0
    assert mock_run.call_count == 1
    mock_run.assert_called_once_with(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_missing_model_pull_and_log(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Missing model: script logs Loading..., runs pull, logs Loaded."""
    config_path = tmp_path / "adapter_config.json"
    config_path.write_text(
        json.dumps(
            {
                "ollama_workstation": {"ollama_models": ["llama3.2", "qwen3"]},
            }
        ),
        encoding="utf-8",
    )
    env = {"ADAPTER_CONFIG_PATH": str(config_path)}
    list_stdout = _ollama_list_output(["llama3.2"])  # qwen3 missing

    with patch.dict(os.environ, env, clear=False):
        with patch("subprocess.run") as mock_run:

            def run_side_effect(*args, **kwargs):
                if args[0] == ["ollama", "list"]:
                    return MagicMock(
                        returncode=0, stdout=list_stdout, stderr=""
                    )
                if args[0][:2] == ["ollama", "pull"]:
                    return MagicMock(returncode=0)
                return MagicMock(returncode=1)

            mock_run.side_effect = run_side_effect
            import ensure_ollama_models as mod  # noqa: E402

            import importlib

            importlib.reload(mod)
            exit_code = mod.main()

    assert exit_code == 0
    out, err = capsys.readouterr()
    assert "Loading model qwen3..." in out
    assert "Loaded model qwen3." in out
    pull_calls = [
        c
        for c in mock_run.call_args_list
        if c[0][0][:2] == ["ollama", "pull"]
    ]
    assert len(pull_calls) == 1
    assert pull_calls[0][0][0] == ["ollama", "pull", "qwen3"]


def test_model_present_with_tag_skips_pull(tmp_path: Path) -> None:
    """Model name with tag (e.g. llama3.2:latest) counts as present."""
    config_path = tmp_path / "adapter_config.json"
    config_path.write_text(
        json.dumps(
            {
                "ollama_workstation": {"ollama_models": ["llama3.2"]},
            }
        ),
        encoding="utf-8",
    )
    env = {"ADAPTER_CONFIG_PATH": str(config_path)}
    list_stdout = _ollama_list_output(["llama3.2:latest"])

    with patch.dict(os.environ, env, clear=False):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=list_stdout, stderr=""
            )
            import ensure_ollama_models as mod  # noqa: E402

            import importlib

            importlib.reload(mod)
            exit_code = mod.main()
    assert exit_code == 0
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["ollama", "list"]


def test_empty_ollama_models_returns_zero_no_pull(tmp_path: Path) -> None:
    """Empty ollama_models list: no pull, return 0."""
    config_path = tmp_path / "adapter_config.json"
    config_path.write_text(
        json.dumps({"ollama_workstation": {"ollama_models": []}}),
        encoding="utf-8",
    )
    env = {"ADAPTER_CONFIG_PATH": str(config_path)}

    with patch.dict(os.environ, env, clear=False):
        with patch("subprocess.run") as mock_run:
            import ensure_ollama_models as mod  # noqa: E402

            import importlib

            importlib.reload(mod)
            exit_code = mod.main()
    assert exit_code == 0
    mock_run.assert_not_called()
