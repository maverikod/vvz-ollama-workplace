<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Shared Quality Gate for Provider Client Unification Plan

This gate is **mandatory** for each step in this plan.

## Where the step list and success metrics are defined

- **Step list and short success criteria:** [atomic/IMPLEMENTATION_PLAN.md](atomic/IMPLEMENTATION_PLAN.md).
- **Per-step description and step-specific success metrics:** [atomic/step_00_scope_freeze.md](atomic/step_00_scope_freeze.md) … [atomic/step_13_integration_tests.md](atomic/step_13_integration_tests.md). Each step file contains a **«Success metric»** section — those are the criteria that must be green to close that step. QUALITY_GATE «step-specific success metrics» refers to that section in the corresponding step document.

## Environment and working directory

- **Working directory:** project root — `/home/vasilyvz/projects/ollama` or the directory that contains `pyproject.toml` and `src/`. **All commands in this gate are run from that directory.** Before running any command, ensure you are in the project root.
- **Virtual environment:** use the project **`.venv`**. **Activate it first**, e.g. `source .venv/bin/activate`. Do not use `--break-system-packages`; install and run all tools and tests inside `.venv`.

## A. Code completeness checks

- No unfinished code.
- No `TODO`, `FIXME`, ellipsis placeholders, or syntax errors.
- No `pass` in production logic (except valid abstract/interface cases).
- No `NotImplemented` / `NotImplementedError` in non-abstract methods.
- No deviations from project rules or this plan.
- No direct workstation → raw redis/ollama paths in runtime flow.

## B. Static checks and formatting

Run from **project root** with **`.venv` activated**. Fix all reported issues after each completed step.

1. **code_mapper** — run exactly one of (depending on how code_mapper is installed):
   - `code_mapper -r /home/vasilyvz/projects/ollama`  
   - or, from project root: `code_mapper -r .`  
   - or, if run as a module: `python -m code_mapper -r /home/vasilyvz/projects/ollama`  
   Use the form that works in this project (CLI entry point or `python -m`). Ensures `code_analysis/` indices are up to date.
2. **black:** `black src tests`
3. **flake8:** `flake8 src tests`
4. **mypy:** `mypy src` (or project-configured scope)

## C. Focused tests

- **Runner:** `pytest`. Run from **project root** with **`.venv` activated**.
- **Focused tests** = tests that cover the **changed behaviour** for the current step. Ways to select:
  - **By path:** `pytest tests/unit/ollama_workstation/test_<module>.py` or `pytest path/to/test_file.py`
  - **By marker:** `pytest -m "not integration"` when the step does not require real services; or a step-specific marker if introduced (e.g. `pytest -m step_04`).
  - **By keyword:** `pytest -k "provider_client" tests/` (or another keyword that matches the changed code).
- If the **step document** (atomic/step_NN_*.md) specifies an exact pytest command in its «Success metric» or «Verification» section, use that. Otherwise, run the minimal set that exercises the changed code.
- Confirm no regressions in changed behaviour.

Additional validation where applicable:

- Provider client config validation must block invalid startup (reject incomplete or conflicting settings).
- Workstation must use only provider clients and proxy-mediated MCP for redis/ollama.

## D. Step closure criteria

A step is complete only when:

- **Step-specific success metrics are green.** Those metrics are **defined in the step description**: open the file for the current step (e.g. step 04 → `atomic/step_04_abstract_base_class.md`) and see its **«Success metric»** section. Satisfy every criterion listed there before closing the step. The full list of steps and their files is in [atomic/IMPLEMENTATION_PLAN.md](atomic/IMPLEMENTATION_PLAN.md).
- A + B + C checks above are all completed and green.
- Step evidence is captured (commands run, key outputs, validation behaviour where applicable).
