# Source Specification — mwps Workspace Orchestration Refactoring

<!-- non-binding -->
**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com

This is the Level 1 human-readable specification (HRS) for refactoring the mwps project (Agent Workstation). Every binding paragraph is prefixed with a stable `{xxxx}` label and is the addressable unit for concept extraction at Level 2. Non-binding material is enclosed in `<!-- non-binding -->` blocks and does not generate requirements.
<!-- /non-binding -->

## Purpose and boundaries

{a1k2} mwps (Agent Workstation) is a logical integration and orchestration layer over an ecosystem of microservices. It coordinates dialogue, context, and tool use across those services rather than implementing their capabilities itself.

{b7m3} All ecosystem servers are built on mcp-proxy-adapter and communicate through a single MCP Proxy over a secured transport — HTTPS, with mutual TLS where the deployment requires it — with automatic registration; clients discover services through the proxy and never hardcode service addresses.

{c4n9} mwps does not itself implement LLM provider access, a local model runtime, chunking, embeddings, semantic search, documentation storage, or plan trees. Each of these responsibilities is delegated to a dedicated ecosystem service, and mwps consumes them as a client.

## Delegation to ecosystem

{d2p5} LLM provider access is delegated to the model-access-core server. mwps invokes its commands `model_session_create`, `model_session_get`, `model_session_delete`, `model_chat`, `model_count_tokens`, `model_estimate_request_capacity`, the `model_cache_*` family, `model_providers`, and `model_health`.

{e8q1} The canonical model types and the `HALError` error type are owned by model-access-core. mwps treats them as the shared contract and does not redefine provider-facing types locally.

{f3r7} The local model runtime is the responsibility of the lmrs zone. mwps never accesses a local runtime directly; all local-runtime access is mediated by model-access-core.

{g6s4} Chunking, embeddings, and semantic search are delegated to the svo, embed, and chunk-metadata-adapter services, consumed through the ready-made `svo-client` and `embed-client` libraries. mwps does not implement its own chunking, embedding, or vector search.

{h9t2} Documentation storage and retrieval are delegated to the doc-store service. mwps reads semantically relevant documentation from doc-store rather than maintaining a local document store.

{j5u8} Plan trees are owned by the plan-manager service. mwps references planner tasks by plan and step identifiers issued by plan-manager and does not maintain its own plan hierarchy.

{k1v6} mwps talks to model-access-core through a single thin client, `mac_provider_client`, built on the `JsonRpcClient` from mcp-proxy-adapter. This client is the only mwps component that speaks the model-access-core protocol.

## Monorepo composition

{m4w3} The `mwps_adapter` subproject, which wrapped a local model runtime as a "Model Workplace Server", is removed from the monorepo. Its role is superseded by delegation to model-access-core and lmrs.

{n7x9} The in-repo provider clients for openai, anthropic, google, xai, and deepseek are removed. All provider access flows through the single `mac_provider_client` to model-access-core.

{p2y5} The in-repo semantic search implementation and its FAISS dependency are removed. Search and retrieval are obtained from the svo, embed, and doc-store services.

{q8z1} The `model_workspace` subproject is retained as the orchestration core of mwps. It owns dialogue orchestration, context assembly coordination, and tool invocation.

{r3a6} The `redis_adapter` server and its `redis_provider_client` are retained. They provide mwps with persistent state storage over the adapter transport.

{s9b4} A new subproject, `context_manager`, is introduced to own context assembly and compression logic.

## Session model

{t2d6} A chat (session) is the unit of dialogue with the workstation and the primary divider of conversation threads. A chat is created explicitly and receives a stable chat identifier. A chat is not bound to a project: over its lifetime, some of its messages may relate to one project, others to a different project, and others to no project at all.

{v8k6} The session is the suspension point of the whole system: every unit of work, every journal record, every context assembly, task activation, and budget accounting hangs off exactly one session. Nothing in the system exists outside a session.

{w3m9} Every session has exactly one owner, fixed at creation: a human or a model. A session owned by a human is a manual session — live dialogue with a person. A session owned by a model is an automatic session — the system talking to itself: plan-chain executions, authoring dispatches, and any other model-to-model work.

{x7n2} Sessions never intersect: they are strictly parallel streams. A message belongs to exactly one session, and no state is shared between sessions. Cross-session connections exist only through durable artifacts — the journal and the plan: an automatic session records what spawned it (the parent session identifier or the plan step), never reaching into another session's messages.

{c7t2} A subagent is simply a session owned by a model. The owning model itself acts within some session, so ownership links sessions into a natural tree rooted in a human-owned session (or in a plan step, for scheduled chain work). Nesting needs no extra mechanism — it is ownership applied recursively, mirroring the subordination concept the ecosystem already applies to tool servers.

{d1u5} Costs aggregate along the ownership chain: a model-owned session's spend counts toward the budgets of the sessions above it, so a human-owned session's budget covers the entire subagent tree spawned beneath it. The journal keeps each session's records separate; only the accounting rolls up.

{e5b8} The orchestrator is the model owning the human-facing session: it converses with the human and holds unrestricted rights — its tool set is not task-scoped, like the Conscience's. To the orchestrator, subagents are smart tools: spawning a subagent appears in its native tool set like any other tool.

{f4c1} Every session carries a spawn flag, fixed at creation: whether its owner model may spawn subagent sessions. The orchestrator's session has it on; leaf executors — for example, chain coders — have it off. Recursion is governed by this flag, never by convention.

{g8d5} A session operates in one of two modes. In dialogue mode the model is invoked on every incoming message — the classic request-reply. In waiting mode the model is not running: the software polls a designated tool, and only when the tool reaches a specified state is the model invoked with the observed result. Waiting costs no tokens.

{h3e9} A subagent runs in one of two modes relative to its owner: in the background — the owner continues its own work and periodically polls the subagent's state; or synchronously — the owner suspends its own work and works only with that subagent until it completes.

{j6f2} The dialogue of any session can be displayed. Every session's message stream — manual or automatic, at any depth of the ownership tree — is renderable from the journal, both as history and as a live tail while the session is running. Viewing is read-only and requires no participation in the session: observation never interferes with the session's flow.

{k4g7} Session presentation follows the session tree, never a single merged feed: each session is shown in its own view — a separate tab. The human-facing chat displays only the orchestrator's own dialogue plus compact status lines for spawned subagents; a subagent's full stream is never dumped inline into the owner's view. To see a subagent's work, the human opens its tab.

{u7e9} Many chats may exist and run concurrently. Chats are isolated from one another: the message history, the rolling summary, the registry of already-shown documentation chunks, the selected tool set, the target model, and the currently active project are all per-chat state.

{v3f1} All per-chat state is stored in Redis, keyed by the chat identifier, through `redis_adapter` and `redis_provider_client`. Closing or archiving a chat does not delete its journal records.

{y5p8} Session identity is issued by the Code Analysis Server's existing client-session mechanism: creating an mwps chat — manual or automatic — creates a CAS client session, and the returned UUID4 becomes the chat identifier. One UUID identifies the session across the entire ecosystem; mwps never mints a second session identity.

{z9q3} Tool servers attach to a session as subordinate sessions under the existing CAS mechanism: the same UUID, linked per server instance (for example, a terminal session for the pair of project and session). Subordinate links are created lazily, when a task first needs that server, and released when the chat closes.

{a6r1} Per-session access roles (CAS RBAC role_ids) are assigned at session creation in accordance with the task's tool policy, giving the slot-5 tool curation a server-side enforcement counterpart: a session physically cannot call what its role forbids.

{b4s7} Closing a chat releases its subordinate links and deletes the CAS client session. Journal records and per-chat state in Redis survive the session's deletion.

{m3y7} User identity is provided by a dedicated identity service that resolves a user to a display name and a uuid4 identifier; mwps does not manage user accounts itself. Every journal record carries the uuid4 of the user on whose behalf the chat runs.

{w5g8} Every model interaction belongs to some session: human dialogues run in manual sessions, and plan-chain executions run in dedicated automatic sessions, so every journal record carries a session identifier — for chain runs alongside the plan and step identifiers.

## Dialogue logging

{t5c2} Every reply in any dialogue with a model is logged automatically. Logging is a property of the dialogue pipeline, not an optional feature invoked per call.

{u1d7} Each log record carries: the chat or session identifier; the project identifier (nullable, empty for a chat outside any project); task links to plan-manager steps — at most one direct and any number of indirect, each expressed as plan plus `step_id` plus the relation type (the set may be empty for unrelated messages); the author of the reply as either `user` or `model`; for a user author, the user's uuid4 from the identity service; for a model author, the model type and the provider as separate fields; and a timestamp.

{k8x4} A model-authored journal record additionally carries the full usage report of the call: input and output tokens, cache writes and cache reads, the computed cost, and latency. These metrics are the raw material for the system's cost and quality accounting.

{v6e3} The dialogue log and the chat history are stored in Redis, accessed through `redis_adapter` and `redis_provider_client`.

## Task threads

{x6j3} A chat has at most one current task — a plan step (plan plus `step_id` from plan-manager) explicitly activated by the user or the orchestrator. The current task is per-chat state and an anchor of the same kind as the current project: activation is explicit, never inferred from message topics.

{y8k5} A journal record has at most one direct task link — to the current task that was active when the message was processed, or to the chain step that produced it. The direct link is deterministic and normative: it marks the message as work on that task.

{z4m2} A record may additionally carry any number of indirect task links, mediated by shared MRS concepts: the context builder tags each message with the concept ids it touches, and the plan steps covering those concepts receive indirect links, with the mediating concepts recorded. Indirect links are advisory retrieval hints; they are never inputs to gates or statuses.

{a2n9} Messages sharing a direct link to the same task form that task's thread. The recent-history slot is thread-aware: for a chat with an active task it is assembled from a core of the most recent messages, plus the active task's thread regardless of age, plus the top indirectly linked materials, all within the slot budget.

{b9p4} Rolling summaries are maintained per thread: digressions and inactive threads are compressed first, and the active task's thread is kept verbatim the longest.

{c3q7} Plan-manager reflects this linkage as runtime parameters of plan steps, kept distinct from the cascade-governed definition fields: at minimum, activation as a current task, execution attempts of chain prompts, and aggregates over directly and indirectly linked journal records (counts and cost). Runtime parameters never mutate the plan definition and never trigger the cascade; exposing them is an external dependency implemented in the plan-manager project.

## Context model

{w2f8} The context constant is the current project — the project the user is working in (or none, for a free chat). It is an anchor, not a boundary: it selects the project's rules and standing standards, keys the per-project persistent cache, and is recorded in every journal entry — while the dialogue itself may freely touch any other projects of the ecosystem without affecting the current project. Retrieval gives priority to the current project's materials but is not restricted to them. Changing the current project is an explicit user action, never inferred from message topics.

{x9g4} The context supplied to a model is assembled from a fixed set of logical blocks called slots. Each slot has a defined source and inclusion rule, and the slots are composed into a single context.

{y3h1} Slot 1 holds the most general rules and is always included in the context.

{z7j5} Slot 2 holds the standards relevant to the previous message. These standards are selected by hybrid cross-search that combines semantic and full-text retrieval over the standards corpus.

{f2t8} The rules and standards corpora served into slots 1 and 2 are stored and indexed in the doc-store service. The source of truth for them remains the project repositories; doc-store ingests them through its file-watcher pipeline, and a corpus change triggers a rebuild of the affected per-project persistent cache objects.

{a4k9} Slot 3 holds tool-usage rules and is included only when the current task involves tools — for example the ai-editor editor or a subset of the analysis server's commands.

{b1m6} Slot 4 holds the chat's recent history: by default the N most recent messages, refined by the thread-aware assembly rule when the chat has an active task.

{c8n2} Slot 5 holds the tools exposed to the working model as native tools: a curated set of at most five to ten, selected per task from the ecosystem's full command pool. Everything else stays reachable indirectly through the generic proxy gateway (`list_servers`, `call_server`, `help`), and the model may request that an additional tool be promoted into its native set mid-task. The default is minimal exposure — only what the task needs.

{d5p3} Slot 6 holds semantically close information retrieved from the doc-store documentation service through `doc_store_client`. Because doc-store is still under development, this slot degrades gracefully: if the service is unavailable, the slot is left empty and processing continues.

{x2r9} Slot 6 uses a three-tier push/pull hybrid. Chunks scoring above a high relevance threshold are inlined in full within the slot budget; chunks in the mid-band are included as one-line annotations (chunk id, source, one-sentence gist); and the working model is given an `expand_docs` tool to pull the full text of any annotated chunk on demand, delivered as a tool result.

{y6t3} A chunk already shown inline earlier in the chat is not inlined again: the dialogue journal tracks the chunk ids that have been shown, and repeated hits appear only as annotations referencing the earlier appearance. The model may re-expand them through the pull tool.

{e2q7} The union of slots 1 through 6 constitutes the "desired context" — the full context that would ideally be supplied before any budget constraint is applied.

{f9r4} The target model is a dynamic attribute of the chat. It can change over the life of the chat and determines the available context window.

{g3s8} The desired context is compressed to fit within the target model's allowed window plus a safe-reserve percentage held back from that window.

{h6t1} Token counting and capacity checks are performed through the model-access-core commands `model_count_tokens` and `model_estimate_request_capacity`. mwps does not estimate token budgets locally.

{j2u5} Context assembly and compression are performed by a cheap model, the "context builder", whose responsibilities are defined in its system prompt.

{k7v9} Compression follows a fixed truncation order: the additional information in slot 6 is dropped first, followed by the M oldest of the N recent messages — but never all N. A core of the recent history is always preserved.

{v4n7} Trimmed history is not discarded: the M oldest messages removed during compression are folded into a rolling summary block that precedes the verbatim recent history. The summary is regenerated infrequently and in batches (hysteresis) rather than on every turn, so it remains a stable, cache-friendly block.

{m1w4} Context management is packaged as the `context_manager` subproject: a library used in-process by `model_workspace`, exposing a command API, and structured so it can be extracted into a standalone adapter server once a second consumer appears.

## Message processing pipeline

{n5x2} A user message is processed in a fixed pipeline: user message → context builder (slot assembly, retrieval, and compression to the model window) → working model with the assembled context → reply delivered to the chat → automatic logging.

{p8y6} The working model uses tools through the MCP Proxy via `list_servers`, `call_server`, and `help`, under a deny-by-default policy. Its tool set is limited to the tools selected for the current task.

{q3z9} The Conscience is a top-tier model whose mandatory role is confined to the top of the plan: HRS work, MRS projection, and concept extraction must receive its verdict before the corresponding artifacts are frozen. Its verdict is very terse and concise. Below those levels there is no mandatory Conscience pass — correctness is enforced structurally, by frozen upper artifacts, coverage matrices, the mechanical gate, the code quality gate, and tier escalation.

{d6r2} Elsewhere the Conscience is an advisory voice: the user or the orchestrator may invoke it at any point of any chat, and its terse assessment is inserted into the message stream as a regular, journal-logged message for further analysis. An advisory Conscience assessment never blocks the delivery of a reply.

{r7a1} The Conscience has access to any tools, without the task-scoped restriction imposed on the working model.

{e9s5} The failure policy is fail-stop: when a required component — model-access-core, Redis, plan-manager, or a provider session — fails or is unreachable, the current processing stops and an error record is written to the journal; no silent degradation or automatic rerouting is performed. The only sanctioned degradations are those stated explicitly in this specification: the empty slot 6 when doc-store is unavailable, and the context builder's fallback model.

## Model invocation

{n8b2} model-access-core provides unification only: a canonical API over providers, sessions, and admission verdicts. All orchestration behavior around a model call — waiting, recovery loops, round limits, user feedback — belongs to mwps. Nothing beyond unification is expected from, or pushed into, the base server.

{p6c4} Every model call goes through a model-access-core session. mwps maintains a lazy registry of mac sessions keyed by role and model: a session is created on first use and reused across chats; switching a chat's target model switches the mac session. Provider credentials never enter mwps.

{q2d9} Submission is two-phase aware: `model_chat` may be accepted, queued, or rejected by admission. mwps waits out queued calls, surfacing the queue state to the user and recording it in the journal; long calls ride the adapter's background-job facility rather than blocking a transport connection.

{r5e7} A `CONTEXT_OVERFLOW` rejection is a signal, not a failure: the context builder performs one deeper compression and the call is retried once; a second overflow is a fail-stop error. Every other `HALError` code fails stop immediately, per the failure policy.

{s7f3} The tool loop is owned by `model_workspace`: each round executes the requested tools through the proxy gateway and issues a new `model_chat` on the same mac session, so the growing prefix stays cached. Tool declarations use the canonical model-access-core tool protocol. The number of rounds is bounded by configuration; exhausting the bound is a fail-stop error, never a silent truncation.

{t3g6} The MVP operates without streaming: replies arrive whole, and user feedback is provided by pipeline-stage events (context assembled, queued at provider, model running, tool round N). Streaming may be added later without changing this contract.

{u9h1} Retries are transport-level only, using client-generated request identifiers and `model_request_status` for reconciliation after a broken connection; semantic auto-retries do not exist. User cancellation maps to `model_request_cancel` and is journaled. Cache operations are executed by `mac_provider_client` on the context builder's plan: the per-project persistent cache object is created on the project's first chat, attached to the relevant mac sessions, and refreshed when the corpus changes.

## Task routing

{p4j8} Every incoming task is triaged by the orchestrator into one of three classes: a dialogue task (question, analysis, discussion), a small change (one or two files, a known pattern, low risk), or a substantial change (new functionality, more than two or three files, architectural decisions, or irreversible effects).

{q6k2} Dialogue tasks and small changes run through the direct pipeline. A small change must additionally pass the code quality gate (formatting, linting, typing, tests), which serves as its equivalent of the plan's mechanical gate.

{r9m5} A substantial change is executed only through a plan in plan-manager. The orchestrator must refuse to execute such a task directly and must initiate a plan instead; no large change bypasses the planner.

{s3n1} The routing class changes only the middle of the pipeline. Automatic journaling (with a null planner reference for unplanned tasks), context cache discipline, and the tiered model roles apply invariantly to all three classes; the advisory Conscience may be invoked in any class.

## Caching

{s2b5} Context blocks are planned to maximize provider cache reuse by keeping stable prefixes across requests, so that the invariant portions of the context are cached rather than re-sent.

{z1u7} Context blocks are ordered by descending stability: general rules, then tool rules and the tool list, then the rolling summary, then the verbatim recent history, then the per-turn volatile retrieval (slots 2 and 6) placed after the history, then the user message. Serialization is deterministic: identical block content always yields identical bytes (canonical key order, no timestamps or randomness in stable blocks).

{a8w5} Per-block token counts are cached in Redis, keyed by the block content hash and the target model's tokenizer profile, so stable blocks are counted once. The safe-reserve percentage scales with the token-count source quality reported by model-access-core: minimal for exact counts, larger for tokenizer estimates, largest for heuristic estimates.

{t9c3} Cache reuse is realized through the model-access-core cache handles. The available cache mode — `persistent`, `inline_ephemeral`, `implicit_only`, or `none` — is determined by the target provider's capability; mwps plans its context blocks to exploit whichever mode the provider offers.

{w8k3} For providers that support a persistent cache, mwps maintains a per-project persistent cache object holding the project's stable context blocks (the general rules and the project's standing standards). The cache object is keyed by the project identifier and is reused across chats within that project. This is a requirement, not an optimization.

## Cost management

{h7v3} Provider prices are obtained automatically by a dedicated pricing microservice. It periodically fetches the providers' published price lists over their ordinary public REST/web endpoints — pricing is not tied to the providers' model APIs and does not belong to model-access-core — versions them, and serves per-token prices to consumers. The cost of every journal record is computed from the prices effective at the moment of the call, never from hardcoded constants.

{j1w6} Spending budgets are configurable per chat, per task, and per calendar day. When a budget is exhausted, the affected work pauses and the situation is escalated to the human; no autonomous work continues past an exhausted budget.

## Model roles and tiering

{m6g3} User communication and task dispatch during planning — the orchestrator role — are performed by a top-tier model, the same tier as the Conscience.

{g5c2} Plan authoring uses tiered models matched to the abstraction level of the artifact. HRS work, MRS projection, and concept extraction are performed by top-tier models (Opus / Fable / GPT-5.5 class). Global steps and tactical steps are authored by mid-tier models (Sonnet / GPT-mini class). Atomic steps are authored by small models (Haiku / GPT-nano class, optionally a local qwen-class model). The tier-to-model mapping is configuration resolved through model-access-core sessions, never hardcoded.

{h2d8} Cheaper authoring at lower levels is structurally guarded: lower-level authors work only from frozen upper artifacts, the coverage matrices, and the standards, and their output must pass the mechanical gate and the level's consistency checks. A gate or consistency failure escalates the artifact to the next model tier up; only after the top tier fails is the defect surfaced to the human.

{j8e4} Every plan artifact records which model authored it — model type and provider as separate fields, consistent with the dialogue journal schema — so plan quality can be traced back to the authoring tier.

{k3f9} For execution, the context builder role is assigned to a Gemini-Flash-class model: a large, cheap context window with flexible explicit provider-side cache management. The per-project persistent cache and the stable slot corpora (rules, standards) are pinned as explicit cache objects with a TTL, so the context builder itself runs almost entirely on cached prefixes. A fallback cheap model is configured for this role through model-access-core sessions in case the primary provider is unavailable.

{n2h7} Within the context builder role, slot selection and assembly run on the cheap primary every turn, while rolling-summary regeneration — the only irreversible compression step — may be routed to a mid-tier model; it runs rarely (hysteresis), so the cost impact is negligible.

## Plan-driven prompt chains

{b3x2} After a plan reaches a green mechanical gate in plan-manager, a prompt chain is assembled from it: for every atomic step, in execution order, a structured set of typed blocks — HRS fragment, MRS fragment, global step, tactical step, atomic step — with blocks shared between steps emitted once and referenced. Chain assembly is a new plan-manager command; it is an external dependency implemented in the plan-manager project and consumed by mwps.

{c5y8} mwps (the context_manager) wraps the raw chain into executable prompts: role-appropriate standards are prepended at the very start of the shared prefix; blocks are serialized canonically and aligned to 256-token boundaries using tokenizer-aware padding; provider cache breakpoints are placed on block boundaries. The 256-token alignment applies to plan prompt chains only, not to dialogue context slots.

{d9z4} Chain prompts share hierarchical prefixes (standards → HRS/MRS fragments and global step → tactical step → atomic step). Two execution orderings are supported: depth-first over the plan tree, which maximizes cache prefix reuse, and dependency waves from the plan graph, which maximizes parallelism. The strategy is chosen per run.

{e4a1} The final executors of chain prompts — the code-writing models — are small models: Haiku / GPT-nano class or a local qwen-class model. Its effective context capacity is not a fixed constant: it is determined by the VRAM remaining after model weights are loaded, via the calibrated per-token KV-cache cost measured by model-access-core hardware calibration. Every assembled atomic prompt — standards, padding, and harness included — together with the reserved output tokens for the generated code is validated against that measured capacity through `model_estimate_request_capacity` at chain assembly time; an overflow routes the step to a larger resident executor tier; if no resident tier fits, the step is first returned for tactical-level subdivision.

{g4u1} Chain assembly includes a volume estimator. When a step cannot fit any resident executor and tactical subdivision cannot make it smaller, an elastic on-demand executor — rented GPU capacity provisioned through the infrastructure service — is brought up for that step and released afterwards. The elastic tier is a principle of this specification; its concrete provisioning details are deliberately deferred.

{f7b6} Every chain prompt execution is logged in the dialogue journal with its plan and step identifiers, closing the end-to-end trace from HRS paragraph to concept, step, prompt, execution, and quality-gate verdict.

## Deprecations

{u4d8} The earlier specifications `refactoring_adapter_structure/SPEC.md` and the analysis under `refactoring_comprehensive_analysis/` are superseded by this specification and must not drive implementation of the refactoring.

<!-- non-binding -->
Ecosystem overview (reference only). The services mwps integrates with, one line each:

- mcp-proxy — single entry point and router; all inter-service traffic passes through it.
- mcp-proxy-adapter — the adapter framework every server and client is built on (transport, registration, command protocol).
- model-access-core — canonical LLM provider access: sessions, chat, token counting, capacity, cache handles, provider health.
- lmrs — local model runtime zone, reached only via model-access-core.
- doc-store — documentation storage and semantic retrieval service.
- svo / svo-client — semantic vector operations service and its client.
- embed / embed-client — embedding service and its client.
- chunk-metadata-adapter — chunking and chunk-metadata service.
- queuemgr — task/queue management service.
- mcp-terminal — terminal command execution service.
- plan-manager — plan tree owner (plans, steps).
- ai-editor — code/text editor exposed as a tool server.
- vast_srv — infrastructure/compute provisioning service.

lmrs is currently contracts-first: its interface contracts exist ahead of a full implementation, so integration relies on the model-access-core delegation path.

Superseded documents kept for history: `docs/plans/refactoring_adapter_structure/SPEC.md` and `docs/plans/refactoring_comprehensive_analysis/`. See the binding Deprecations paragraph above for their normative status.

Deferred by owner decision (2026-07-06): the resource-usage permission model (rights of sessions/roles over compute, providers, and services beyond the CAS RBAC roles already bound above) is intentionally not specified here. It will be added by cascade after the current scope is implemented.
<!-- /non-binding -->
