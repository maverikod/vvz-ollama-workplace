# STEP-12 — scripts/verify_context_formation.py: fix E402 noqa

**File:** `scripts/verify_context_formation.py`  
**Size:** unknown  
**Issues:** 15× Flake8 E402 — module-level imports not at top of file  
**Severity:** 🟢 Low (style only, functionality unaffected)  
**Depends on:** —  
**Blocks:** —

---

## Problem

Flake8 reports 15 `E402: module level import not at top of file` errors,
all at lines 21–26 of `scripts/verify_context_formation.py`.

This is a standard pattern in diagnostic/verification scripts:
```python
import sys
import os

# Adjust path before importing project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import mwps  # E402
from mwps.config import load_config  # E402
```

The `sys.path` manipulation before imports is intentional and necessary
for standalone script execution without installation.

## Task

Add `# noqa: E402` to each affected import line:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import mwps  # noqa: E402
from mwps.config import load_config  # noqa: E402
# ... repeat for all 15 lines
```

Alternatively, add a `# flake8: noqa: E402` file-level comment at the top
if all E402s in this file are intentional (simpler, one change):

```python
#!/usr/bin/env python
# flake8: noqa: E402
"""Verify context formation pipeline."""
```

Prefer the file-level comment since all 15 errors are in the same block.

## Acceptance criteria

- [ ] `flake8 scripts/verify_context_formation.py` reports 0 errors
- [ ] Script still runs correctly (path manipulation unchanged)
- [ ] One-line fix preferred (file-level `# flake8: noqa: E402`)
