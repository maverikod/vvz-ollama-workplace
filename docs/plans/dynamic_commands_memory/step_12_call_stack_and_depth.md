# Step 12: Call stack and model-call depth guard

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Maintain a call stack for model invocations triggered by tools; enforce max_model_call_depth before starting a nested model call. One step = one file (this doc).

## Goal

- **CallStack:** Per request (or per chat flow): stack of frames (e.g. tool_name, depth). Depth 0 = top-level chat. When a model-calling tool runs, push (tool_name, depth+1); when it returns, pop.
- **ModelCallDepthGuard:** Before starting a model invocation from a tool: if current_depth >= max_model_call_depth, do not call the model; return an error to the caller (e.g. "max recursion depth exceeded"). Otherwise allow and push.
- **ModelCallingToolAllowList:** Set of command_ids that are allowed to trigger a model call (e.g. ollama_chat). Others are plain RPC and must not invoke the model through this path.
- Config: **max_model_call_depth** (e.g. 1 or 2).

## Objects

- **CallStack:** push(tool_name, depth), pop(), current_depth() -> int. Lifecycle: created at entry (e.g. first ollama_chat); discarded when top-level flow completes.
- **ModelCallDepthGuard:** can_enter_model_call() -> bool; or check and raise. Uses CallStack and config max_model_call_depth.
- **ModelCallingToolAllowList:** may_call_model(command_id) -> bool. Config or fixed set.

## Inputs / outputs

- **Input (guard):** Current call stack state; config max_model_call_depth.
- **Output (guard):** True if nested call is allowed; False or raise if depth exceeded.
- **Input (allow-list):** command_id (after resolution from display_name).
- **Output (allow-list):** True if this tool may invoke the model.

## Acceptance criteria

- At depth 0, a model-calling tool can start a nested call (depth 1). At depth >= max_model_call_depth, nested call is rejected with a clear error.
- Only tools in the allow-list can trigger model invocation; others execute as normal tools and do not push to call stack.
- Same session_id is used for nested calls (enforced by chat flow; this step only provides stack and guard).

## References

- Main plan: [§5.3 Call stack and recursion depth](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#53-call-stack-and-recursion-depth), [§5.5 Recommendation](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#55-recommendation-draft).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (CallStack, ModelCallDepthGuard, ModelCallingToolAllowList), [diagram: tool invokes model](00_objects_and_diagrams.md#5-diagram-tool-invokes-model-call-stack-and-depth).
- Prev: [step_11_documentation_source.md](step_11_documentation_source.md). Next: [step_13_session_commands.md](step_13_session_commands.md). Chat flow / tool executor use these.

## Success metrics

- **Step-specific:** CallStack push/pop/current_depth; at depth 0 model-calling tool can enter; at depth >= max_model_call_depth nested call rejected with clear error; only allow-listed command_ids can trigger model; config max_model_call_depth and allow-list.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Recursion | chat_flow has no depth limit; ollama_chat can be called as tool | Before invoking model from tool: check ModelCallDepthGuard; push/pop CallStack | CallStack, ModelCallDepthGuard, ModelCallingToolAllowList; config max_model_call_depth |
| Tools | ollama_chat is effectively model-calling | — | Allow-list identifies which command_ids may call model (e.g. ollama_chat.ollama-adapter) |
| **Config generator / validator** | — | — | When adding max_model_call_depth and allow-list config: update generator overlay and `validate_project_config` per main plan §6.4 (adapter first, project on top). |

## Dependencies

- Config. Chat flow (or tool executor) uses CallStack, ModelCallDepthGuard, ModelCallingToolAllowList when a tool execution would invoke the model.

## Deliverable

- CallStack, ModelCallDepthGuard, ModelCallingToolAllowList. Config for max_model_call_depth and allow-list. Unit tests.
