# Step 18: Final Real WS Gate

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `scripts/verify_real_ws_e2e.py`

## Dependencies
- `NAMING_FREEZE.md` (mandatory naming/source of truth)
- `../QUALITY_GATE.md`

## Detailed scope
- Final release gate over real infrastructure.
- Mandatory WS path verification.
- Includes negative TLS scenario.
- Blocks release on any failure.

## Success metric
- Gate exits `0` only when real WS E2E is healthy for model-workspace and database flows.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
