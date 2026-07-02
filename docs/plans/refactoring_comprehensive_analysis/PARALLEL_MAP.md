# Parallel Execution Map

**Plan:** `refactoring_comprehensive_analysis`  
**Total steps:** 12  
**Minimum sequential depth:** 4 waves

---

## Dependency graph

```
WAVE 1 (parallel, no deps)
├── STEP-01  chat_flow.py              🔴 split
├── STEP-02  config.py                 🔴 split + dup
├── STEP-04  get_model_context_cmd     🔴 split + placeholder
├── STEP-06  commercial_chat_client    🔴 NOT IMPLEMENTED
├── STEP-10  documentation_slot_builder 🔴 STUB
├── STEP-11  model_workspace_client    🟡 dup
└── STEP-12  scripts/verify_context    🟢 flake8

WAVE 2 (after deps complete)
├── STEP-03  mwps_chat_command       🔴 split + dup     ← needs STEP-01
├── STEP-05  docker_config_validation  🔴 split          ← needs STEP-02
└── STEP-07  provider_registry         🔴 NOT IMPL       ← needs STEP-06

WAVE 3
└── STEP-08  provider_client_base      🟡 dup (ABC)       ← needs STEP-06, STEP-07

WAVE 4
└── STEP-09  mwps_provider_client    🟡 dup normalize   ← needs STEP-08
```

---

## Wave details

### Wave 1 — 7 steps in parallel

| Step | File | Issue | Est. effort |
|------|------|-------|-------------|
| STEP-01 | `chat_flow.py` | Split 609-line file | M |
| STEP-02 | `config.py` | Split + merge 2 dups | M |
| STEP-04 | `get_model_context_command.py` | Split + fix placeholder | M |
| STEP-06 | `commercial_chat_client.py` | Implement 2 NOT IMPL | L |
| STEP-10 | `documentation_slot_builder.py` | Implement 2 STUB | S |
| STEP-11 | `model_workspace_client/config_cli.py` | Extract shared arg parser | S |
| STEP-12 | `scripts/verify_context_formation.py` | Add noqa comment | XS |

### Wave 2 — 3 steps in parallel (after Wave 1)

| Step | File | Issue | Waits for |
|------|------|-------|----------|
| STEP-03 | `mwps_chat_command.py` | Split + move schemas | STEP-01 |
| STEP-05 | `docker_config_validation.py` | Split monolith | STEP-02 |
| STEP-07 | `provider_registry.py` | Implement 3 NOT IMPL | STEP-06 |

### Wave 3 — 1 step (after Wave 2)

| Step | File | Issue | Waits for |
|------|------|-------|----------|
| STEP-08 | `provider_client_base.py` | Convert to ABC | STEP-06, STEP-07 |

### Wave 4 — 1 step (after Wave 3)

| Step | File | Issue | Waits for |
|------|------|-------|----------|
| STEP-09 | `mwps_provider_client.py` | Eliminate dup normalize | STEP-08 |

---

## Effort estimates

| Size | Meaning | Steps |
|------|---------|-------|
| XS | <30 min, 1 edit | STEP-12 |
| S | 30–60 min, <5 edits | STEP-10, STEP-11 |
| M | 1–3h, file split or impl | STEP-01–09 |
| L | 3–6h, new logic + tests | STEP-06, STEP-07 |

---

## Critical path

Longest dependency chain: **STEP-06 → STEP-07 → STEP-08 → STEP-09**

This chain unblocks commercial provider support. Must be completed sequentially.
All other steps are independent of this chain and can proceed in Wave 1.

---

## Recommended execution order for a single developer

1. Start Wave 1 in this priority order:
   - STEP-12 (5 min, clears flake8)
   - STEP-06 (critical path start)
   - STEP-10, STEP-11 (quick wins)
   - STEP-01, STEP-02, STEP-04 (splits)
2. Wave 2 after Wave 1 completes
3. Wave 3 → Wave 4

**Total estimated effort:** 12–18 hours sequential / 6–8 hours with parallelism (2 developers)
