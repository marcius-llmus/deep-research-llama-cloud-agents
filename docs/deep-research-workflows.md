# Deep Research Workflows Specification (LlamaIndex Workflow + Function Agent Tools)

This document specifies the backend workflow design for a **Deep Research Agent** implemented using **LlamaIndex Workflows** and deployed with the existing repository conventions:

- Workflows are served via `llamactl serve`.
- Progress is streamed to the UI using workflow events.
- Configuration is loaded via `ResourceConfig` from `configs/config.json`.
- Llama Cloud access is injected via `Resource(get_llama_cloud_client)` from `src/deep_research/clients.py`.
- Persisted records are written to **Agent Data** idempotently (delete/replace by stable identifier).

---

## 1) Goals

### Primary goals
1. **Two-phase execution contract**
   - Phase A: planning & clarification (**no web search/retrieval**)
   - Phase B: execution (web search + retrieval + parsing + synthesis)

2. **Live report patching**
   - Maintain a living `report_markdown` in workflow state.
   - The agent updates the report incrementally as new information arrives.
   - The report is always **authoritative in agent context**; the UI updates from FunctionAgent tool results.

3. **Traceability**
   - Store sources and artifacts.
   - Enable the UI to show “all data about the research session”.

---

## 2) Workflows overview

### 2.1 Research Metadata Workflow
**Name:** `research-metadata` (registered in `pyproject.toml`)

**Purpose:** Provide the UI with runtime configuration.

**Inputs:** none

**Outputs:**
- `research_collection` (Agent Data collection name)
- optional `research_settings_schema` (JSON Schema to drive a dynamic settings form)

This follows the same metadata workflow pattern used throughout the repo: load config via
`ResourceConfig`, resolve `$ref`s, and return a small, UI-friendly payload.

---

### 2.2 Research Workflow
**Name:** `deep-research`

**Purpose:** Orchestrate planning, approval gate, web research, parsing, synthesis, patching, persistence.

**High-level graph:**
1. `draft_plan`
2. `await_approval`
3. `run_web_research`
4. `fetch_parse_sources` (loop/batch)
5. `synthesize_and_patch` (loop/batch)
6. `persist_session`

---

## 3) State model (“agent context”)

Workflow state is the authoritative in-run context. It must be stored using `Context[StateModel]` and mutated via `ctx.store.edit_state()`.

### Recommended fields

```json
{
  "research_id": "uuid",
  "status": "planning|awaiting_approval|running|completed|failed",
  "initial_query": "string",
  "settings": {
    "patch_chunk_size": 800,
    "max_search_results_per_query": 5,
    "max_sources": 20
  },
  "plan": {
    "clarifying_questions": [],
    "expanded_queries": [],
    "outline": []
  },
  "sources": [
    {
      "url": "...",
      "title": "...",
      "retrieved_at": "...",
      "snippet": "...",
      "file_id": "...",
      "notes": "..."
    }
  ],
  "artifacts": [
    { "file_id": "...", "name": "...", "kind": "pdf|html|text", "source_url": "..." }
  ],
  "report_markdown": "...",
  "events": []
}
```

Notes:
- `report_markdown` is always valid markdown.
- Detailed run tracing is provided via the agent/workflow event stream (`AgentStream`, `ToolCall`, `ToolCallResult`, `AgentInput`, `AgentOutput`, `StopEvent`, `WorkflowCancelledEvent`).

Important:
- During an active run, the **live** `report_markdown` exists in the agent/workflow context (state) and is updated
  there first. Persisting to Agent Data is optional and provides only a snapshot for reload/resume.

---

## 4) Approval gating (HITL)

The system must not access the web until explicit user approval.

Two acceptable patterns:

### Pattern A: Single handler with approval event (recommended)
- The workflow enters an `await_approval` step that pauses.
- UI sends an `ApproveEvent` to the running handler.
- When received, execution continues.

### Pattern B: Two workflows
- `deep-research-plan` generates plan and stores session (status: awaiting approval).
- UI triggers `deep-research-execute` after approval.

Pattern A provides the most “agent-like” interactive flow.

---

## 5) Events streamed to UI

Events are the UI’s source of truth for progress and live report updates. Payloads should be user-readable and serializable.

The workflow must stream the **actual agent/workflow events** consumed by the UI (per the provided handler mapping):

- `AgentStream` (assistant streaming output)
- `ToolCall`
- `ToolCallResult`
- `AgentInput`
- `AgentOutput`
- `StopEvent`
- `WorkflowCancelledEvent`

No separate “domain events” (like `PlanReady`, `SourceAdded`, `ReportUpdated`) should be emitted. All UX-relevant progress must be represented through the FunctionAgent event stream (tool calls/results, agent streaming text, lifecycle events) and/or persisted session snapshots in Agent Data.

---

## 6) Tooling: Function Agent + tools

The deep research logic is implemented as a **Function Agent** that can invoke a constrained set of tools.

Tooling rules:
- Tools MUST be implemented using a `BaseToolSpec`-style interface (e.g., `BaseToolSet` / `spec_functions`) so the
  agent can register tool functions in a consistent, typed way.
- Tool inputs/outputs SHOULD be typed (Pydantic models or structured dicts) so `ToolCallResult[T]` payloads are stable.

The workflow orchestrates steps; the agent handles reasoning and tool selection within a step. The workflow must
stream only the FunctionAgent events listed in this doc.

### 6.1 Tool: Query decomposition (NO web)
**Name:** `decompose_query`

**Input:**
- `initial_query: str`
- optional constraints (audience, region, timeframe)

**Output:**
- `clarifying_questions: list[str]`
- `expanded_queries: list[str]`
- `outline: list[str]`
- optional assumptions

Rules:
- Must not call any web tools.
- Should propose a plan that can be displayed and approved.

---

### 6.2 Tool: Web search
**Name:** `web_search`

**Input:**
- `query: str`
- `max_results: int`

**Output:**
- list of `{ url, title?, snippet? }`

Rules:
- Can only be invoked after approval.
- Must deduplicate URLs across queries.

---

### 6.3 Tool: Fetch page content
**Name:** `fetch_url`

**Input:**
- `url: str`

**Output:**
- `{ content_type, raw_bytes?, text?, html? }`

Rules:
- Wrap network errors; emit user-friendly Status.
- Respect timeouts and size limits.

---

### 6.4 Tool: Parse/normalize content (LlamaIndex parsing)
**Name:** `parse_content`

Purpose:
- Convert complex documents (HTML, PDF, DOCX) into structured text/nodes.

**Input:**
- `content: bytes|str`
- `content_type: str`

**Output:**
- `{ text: str, sections?: [...], metadata?: {...} }`

Rules:
- Prefer LlamaIndex readers/parsers.
- Keep metadata for citations.

---

### 6.5 Tool: Update report incrementally
**Name:** `update_report`

**Input:**
- `current_report_markdown: str`
- `outline: list[str]`
- `new_notes: str|structured`
- `max_update_size: int` (user-configured)

**Output:**
- `new_report_markdown: str`
- optional `reason: str`

Rules:
- The update must be bounded by `max_update_size`.
- The update must preserve markdown validity and the agreed outline.

### Report update signaling (required)
To support live report updates in the UI using **only FunctionAgent events**:

- The `ToolCallResult[UpdateReportResult]` emitted for `update_report` MUST include `new_report_markdown`.
- The workflow MUST also update the in-memory agent context (`report_markdown` in state) before emitting the tool result.
- Persisting the updated report to Agent Data is optional and treated as a snapshot.

---

Note: this system does **not** track a patch history. Instead, the UI derives “what happened” from the FunctionAgent event stream (tool calls/results, logs) and from persisted session fields (report, sources, artifacts).

---

## 7) Artifacts and downloaded files

To support a rich UI, the workflow should persist artifacts where possible.

### Recommended approach
- When fetching a source:
  - store a snapshot (raw HTML, extracted text, or downloaded PDF) as a **Llama Cloud File** when feasible
  - record the returned `file_id` in `sources[].file_id` and/or `artifacts[]`

This enables file previews in the UI.

---

## 8) Persistence (Agent Data) and idempotency

Each research session is persisted to Agent Data under a stable identifier: `research_id`.

### Idempotent write pattern
1. `delete_by_query(filter={"research_id": {"eq": research_id}})`
2. `agent_data(data=session_record, collection=RESEARCH_COLLECTION)`

Persist at minimum:
- on plan ready (status awaiting approval)
- periodically during execution (optional)
- at completion (final report)

---

## 9) Configuration (`configs/config.json`)

All runtime settings must be loaded via `ResourceConfig`.

### Proposed config section

```json
{
  "research": {
    "settings": {
      "max_report_update_size": 800,
      "max_search_results_per_query": 5,
      "max_sources": 20,
      "timeout_seconds": 600
    },
    "collections": {
      "research_collection": "research-sessions"
    }
  }
}
```

---

## 10) Error handling

- Wrap external calls (search, fetch, file ops) in try/except.
- Always stream a clear `Status(level="error", message=...)` before failing.
- Prefer failing fast for unrecoverable errors (missing config, invalid approval state).

---

## 11) Registration

All new workflows must be registered in `pyproject.toml` under:

```toml
[tool.llamadeploy.workflows]
research-metadata = "deep_research.research_metadata_workflow:workflow"
deep-research-plan = "deep_research.research_plan_workflow:workflow"
```

Names must remain stable because the frontend references them.
