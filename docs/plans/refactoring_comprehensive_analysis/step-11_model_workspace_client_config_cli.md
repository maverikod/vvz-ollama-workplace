# STEP-11 — model_workspace_client/config_cli.py: deduplicate arg parsers

**File:** `src/model_workspace_client/config_cli.py`  
**Size:** 388 lines (within limit)  
**Issues:** `_parse_validate_args` (lines 129–141) and `_parse_test_connection_args` (lines 286–300) are near-identical (similarity 1.0)  
**Severity:** 🟡 Medium  
**Depends on:** —  
**Blocks:** —

---

## Current structure (relevant)

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `_parse_validate_args` | 129–141 (13) | Parse args for `validate` subcommand |
| `_parse_test_connection_args` | 286–300 (15) | Parse args for `test-connection` subcommand |

## Problem

Both functions parse the same set of arguments (`--config`, `--host`, `--port`, possibly `--timeout`)
for different CLI subcommands, using identical `argparse` setup blocks.
This is a textbook case of copy-paste that grows independently.

## Task

### 11a. Extract shared arg-parser factory

```python
def _add_connection_args(parser: argparse.ArgumentParser) -> None:
    """
    Add common connection arguments (config, host, port) to a subcommand parser.

    Args:
        parser: Subcommand parser to augment.
    """
    parser.add_argument("--config", ...)
    parser.add_argument("--host", ...)
    parser.add_argument("--port", ...)
```

### 11b. Refactor both parsers

```python
def _parse_validate_args(subparsers) -> None:
    p = subparsers.add_parser("validate", ...)
    _add_connection_args(p)
    # validate-specific args only

def _parse_test_connection_args(subparsers) -> None:
    p = subparsers.add_parser("test-connection", ...)
    _add_connection_args(p)
    # test-connection-specific args only
```

## Acceptance criteria

- [ ] `_add_connection_args` helper extracted
- [ ] Both `_parse_validate_args` and `_parse_test_connection_args` use it
- [ ] No duplicated `add_argument` calls
- [ ] CLI behavior unchanged (same flags, same defaults)
- [ ] `lint_code` + `type_check_code` pass
