<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Adapter Baseline Sources (for Steps 01-12)

This document defines the mandatory source of truth for:

- `adapter config files`
- `adapter base generator/validator primitives`

All steps `step_01` ... `step_12` must reference this document and use it during implementation.

## 1) Adapter config files (source of truth)

Use the adapter-oriented config format already used in this project.

Primary baseline files:

- `config/adapter_config.local.json.example` (canonical local example)
- generated adapter configs produced by project generators/CLIs in this plan

Rule:

- Do not introduce a parallel config format.
- Generator and validator implementations must read/write/validate the same adapter config contract.

## 2) Adapter base generator/validator primitives

Reuse existing adapter primitives instead of implementing parallel logic.

Primary sources:

- project dependency `mcp-proxy-adapter` (client/config/registration patterns)
- existing project implementations discoverable via `code_analysis/*` and current `src/*/config_generator.py`, `src/*/config_validator.py`

Mandatory implementation protocol:

1. Before coding, inspect `code_analysis/*` for existing generator/validator helpers.
2. Reuse adapter primitives from existing code or `mcp-proxy-adapter` where possible.
3. If a required primitive is missing, add the minimal extension and document it in step evidence.

## 3) Verification expectation

For each step that implements generator/validator logic:

- step evidence must list which adapter config contract was used;
- step evidence must list which existing primitive(s) were reused;
- if new primitive code was added, evidence must explain why reuse was impossible.
