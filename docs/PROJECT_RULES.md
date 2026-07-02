<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Project Rules

Rule IDs: `CR-*` (core), `LAYOUT-*` (repository layout). Role behavior:
`docs/agent-ref/roles/`.

## 0. Project Profile

| Key | Value |
|-----|-------|
| `PROJECT_NAME` | `Agent Workstation` |
| `PROJECT_SLUG` | `mwps` |
| `PROJECT_ID_UUID4` | `c9bda962-4a28-4a15-b2bd-0e12b7f41ff9` |
| `PRIMARY_LANGUAGE` | `Python` |
| `PACKAGE_ROOT` | `src/` |
| `TEST_FRAMEWORK` | `pytest` |
| `CHAT_LOCALE` | `ru` |
| `ARTIFACT_LOCALE` | `en` |
| `HEADER_AUTHOR` | `Vasiliy Zdanovskiy` |
| `HEADER_EMAIL` | `vasilyvz@gmail.com` |

## 1. Precedence

1. Current user message: explicit instruction wins.
2. Safety and repository boundary: `CR-002`.
3. Active role contract: `docs/agent-ref/roles/<role>.yaml` plus
   `common.yaml` and, for tool-using work, `tooling.yaml`.
4. This file: `CR-*`, `LAYOUT-*`, and the project profile.
5. Tool and harness defaults.

## 2. Core Rules

| ID | Rule |
|----|------|
| **CR-001** | Execute the current task literally; do not skip or dilute stacked instructions. |
| **CR-002** | Do not modify paths outside this repository without explicit user permission. |
| **CR-003** | Root `projectid` file must exist and be valid JSON with `id` UUID4 and `description`. Missing or invalid means stop and report. |
| **CR-004** | Questions and analysis-only tasks are answered in chat, not by creating unsolicited files. Durable docs only when the task is to write them. |
| **CR-005** | Before the first action of a kind (edit, search, terminal), read the matching manual named in `docs/agent-ref/roles/tooling.yaml`; do not act from memory of a standard. |
| **CR-006** | After changing production code, the tester gate should pass: black, flake8, mypy, and pytest, scoped when appropriate. Report any check that could not be run. |
| **CR-007** | Chat with the user in `CHAT_LOCALE`; repository artifacts are in `ARTIFACT_LOCALE` unless the user specifies otherwise. |
| **CR-008** | Commit only when the user asks. Push only when the user asks. |
| **CR-009** | Run independent searches, reads, and checks in parallel when possible. |
| **CR-010** | Plans follow `docs/standards/plan_standard_machine.yaml`; tactical and atomic steps follow the shipped planning standards. |
| **CR-011** | Prompts are tool-agnostic. `AGENTS.md` and `docs/agent-ref/roles/*.yaml` must contain no mechanics of concrete external services, servers, or proxies. Tool specifics live in `docs/standards/`, referenced through `tooling.yaml: manuals`. |

## 3. Repository Layout

| ID | Rule |
|----|------|
| **LAYOUT-01** | Production code lives under `src/`. |
| **LAYOUT-02** | Automated tests live under `tests/`, mirroring package structure where helpful. |
| **LAYOUT-03** | Durable documentation lives under `docs/`. |
| **LAYOUT-04** | Agent role contracts live under `docs/agent-ref/roles/`. |
| **LAYOUT-05** | Machine standards live under `docs/standards/`. |
| **LAYOUT-06** | Development plans live under `docs/plans/`. |
| **LAYOUT-07** | Working AI outputs, audits, and reports live under `docs/ai-reports/` or the existing `docs/reports/` when matching older project convention. |
| **LAYOUT-08** | Change or feature requests to external teams live under `docs/requests/`. |
| **LAYOUT-09** | Ops and maintenance scripts live under `scripts/`; non-test harnesses do not live in `tests/`. |

