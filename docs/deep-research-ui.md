# Deep Research UI Specification

This document specifies the UI/UX and frontend architecture for a **Deep Research** experience built on top of the existing codebase (`ui/`) and its conventions:

- UI is configured at runtime by backend **metadata** workflows.
- Workflows are invoked/observed via `@llamaindex/ui` workflow hooks.
- Agent Data is used for persistent session storage.
- No ad-hoc clients inside pages; all client construction stays centralized in `ui/src/lib/client.ts` and providers.

---

## 1) Goals

### Primary goals
- Support a **two-phase** research flow:
  1. **Plan phase** (no web access): clarify theme, decompose into queries, propose outline, ask for approval.
  2. **Execution phase**: web search + retrieval + parsing + synthesis.
- Show **all data** related to a research session:
  - initial user query
  - plan (expanded queries, outline, assumptions)
  - sources visited and retrieved
  - downloaded artifacts/files (when available)
  - event log / run log
  - live-updating **final report** that grows over time
- Provide a modern “research cockpit” experience: live progress, traceability, exports.

### Non-goals
- Do not hardcode schema fields or collection names.
- Do not introduce a new global state manager unless necessary.
- Do not bypass metadata-driven wiring.

---

## 2) Runtime metadata and collections

The app must obtain required runtime metadata via a backend workflow (e.g. `research-metadata`).

### Metadata response (conceptual)
The frontend expects a shape similar to:

```ts
type ResearchMetadata = {
  research_collection: string;   // Agent Data collection for research sessions
  artifacts_collection?: string; // optional, if separating artifacts
  research_settings_schema?: any; // optional JSON schema for settings form
};
```

Notes:
- If only one collection is used, `research_collection` is required.
- If a settings schema is provided, the UI renders a dynamic “Settings” form.

---

## 3) Information architecture (routes)

The router remains consistent with the existing `HashRouter` pattern.

### Proposed routes
- `#/research` — Research dashboard (session list + create new)
- `#/research/:researchId` — Research session detail page (tabs)

Optional (phase 2 enhancements)
- `#/research/:researchId/run/:handlerId` — Deep link to a specific run handler

---

## 4) Core pages

### 4.1 Research Dashboard (`/research`)

**Purpose:** entry point for creating and managing research sessions.

**Layout:**
- Header: title + action buttons
  - “New research”
- Main panel:
  - Create form:
    - `Goal / Theme` (textarea)
    - optional dynamic settings form (from metadata schema)
    - “Generate Plan” button
  - Recent sessions list:
    - table/grid of sessions (most recent first)
    - columns: Title/Goal, Status, Last updated, #Sources, #Files
    - clicking navigates to `/research/:researchId`

**Data source:**
- Agent Data search in `research_collection`, sorted by `updated_at` or stored timestamps.

**Empty state:**
- If no sessions exist, show an onboarding card explaining the two-phase flow.

---

### 4.2 Research Session Detail (`/research/:researchId`)

**Purpose:** show ALL session data and provide the live research cockpit.

#### Header
- Session title (derived from goal, or explicit `title` field)
- Status pill: `planning | awaiting_approval | running | completed | failed`
- Primary actions:
  - `Approve & Start Research` (only when awaiting approval)
  - `Resume` / `Run again` (if supported)
  - `Export` (markdown/json)

#### Body: Tabs

1) **Overview**
   - Initial query/goal
   - Plan summary
   - Research configuration used
   - Metrics: sources, files, runtime, tokens/cost (if available)
   - Latest updates

2) **Live Report**
   - Render `report_markdown` with a clean markdown renderer
   - A “Last updated” timestamp
   - Report updates are reflected live when the event stream indicates the report changed (see **Event contract**).

3) **Sources**
   - List of sources with:
     - URL, domain, title, retrieved_at
     - short excerpt/snippet
     - tags/labels (optional)
   - Clicking a source opens a side panel showing:
     - extracted notes
     - citation references used in report

4) **Files / Artifacts**
   - Gallery/list of artifacts:
     - `name`, `kind` (pdf/html/text), `created_at`
     - `file_id` (if stored as Llama Cloud File)
   - Preview:
     - If `file_id` exists, reuse existing file preview component patterns.

5) **Run Log**
   - Chronological FunctionAgent/workflow event stream (see Event contract below):
     - agent streaming output
     - tool calls + tool results
     - explicit agent input/output markers
     - workflow lifecycle (stop/cancel)
   - Support filtering by level (info/warn/error).

---

## 5) User flow (two-phase)

### Step 1: Plan
1. User enters theme/goal and clicks **Generate Plan**.
2. UI starts a workflow handler (plan step).
3. UI subscribes to workflow events:
   - shows progress
   - when plan is ready, renders a “Plan review” card

### Step 2: Approval
4. User reviews:
   - clarifying questions
   - expanded queries
   - proposed outline
5. User clicks **Approve & Start Research**.
6. UI sends an approval event to the existing handler **or** starts a second “execute” workflow run (depending on backend design).

### Step 3: Execute + Live report
7. UI shows:
   - progress stream
   - sources being added
   - live report updates (patched incrementally)

### Step 4: Completion
8. UI shows final status and enables exports.

---

## 6) Event contract (frontend expectations)

Frontend subscribes to handler events and updates local UI state.

The UI must be built around the **actual event types produced by the FunctionAgent/workflow stream** (per the provided handler mapping):

- `AgentStream`
- `ToolCall`
- `ToolCallResult`
- `AgentInput`
- `AgentOutput`
- `StopEvent`
- `WorkflowCancelledEvent`

### Agent/workflow stream events (required)

#### `AgentStream`
Purpose: incremental assistant output (tokens/chunks).

UI behavior:
- Append streamed text into the “Assistant output” panel.
- Optionally group output by phase (planning vs execution).

#### `ToolCall` / `ToolCallResult`
Purpose: trace tool usage.

UI behavior:
- Render a tool timeline with expandable inputs/outputs.
- If the tool is `update_report`, refresh the report panel. Preferred approaches (in order):
  1. If the `ToolCallResult` includes `new_report_markdown`, update the report immediately.
  2. Otherwise, re-fetch the session record from Agent Data (eventual consistency).

#### `AgentInput` / `AgentOutput`
Purpose: explicit agent input/output markers (useful for separating planning artifacts from execution artifacts).

UI behavior:
- Display as structured log entries (optionally collapsed by default).

#### `StopEvent`
Purpose: marks workflow completion and provides the final result payload.

UI behavior:
- Mark run as completed.
- Refresh session record from Agent Data and enable exports.

#### `WorkflowCancelledEvent`
Purpose: marks a cancelled run.

UI behavior:
- Mark run as cancelled.
- Stop streaming and leave the UI in a recoverable state.

---

## Report update contract (how the UI knows the report changed)

Because the system uses **only FunctionAgent events**, the UI must treat the following as authoritative signals that the report changed:

1. A `ToolCallResult` for tool `update_report` that contains `new_report_markdown`.
2. If the backend persists the session record after report updates, the UI may also periodically refresh the session record from Agent Data when it observes:
   - `ToolCallResult(update_report)` (even if it does not include the report inline)
   - `StopEvent`

The UI must **not** depend on separate domain events like `ReportUpdated`.

## 7) Session record (Agent Data shape)

The UI should be able to render from a single “session record” retrieved from Agent Data.

Minimum recommended fields:

```json
{
  "research_id": "...",
  "status": "planning|awaiting_approval|running|completed|failed",
  "created_at": "...",
  "updated_at": "...",
  "initial_query": "...",
  "plan": {
    "clarifying_questions": [],
    "expanded_queries": [],
    "outline": []
  },
  "report_markdown": "...",
  "sources": [
    {
      "url": "...",
      "title": "...",
      "retrieved_at": "...",
      "snippet": "...",
      "file_id": "..."
    }
  ],
  "artifacts": [
    { "file_id": "...", "name": "...", "kind": "pdf|html|text", "source_url": "..." }
  ]
}
```

---

## 8) Exports

Provide exports from the Session Detail page:

- Markdown: `report_markdown` download
- JSON: full session record download

Optional:
- “Sources CSV” export

---

## 9) Styling / UX guidelines

- Use existing Tailwind and UI conventions (avoid new styling systems).
- Keep a consistent layout with the existing toolbar context:
  - breadcrumbs: `Research > <Session>`
  - action buttons in the toolbar
- Provide clear run states and disable buttons while actions are in progress.
- Show errors in a visible but non-blocking way (toast/banner + log entries).

---

## 10) Implementation notes (non-code)

- Add a `ResearchPage` and `ResearchSessionPage` under `ui/src/pages/`.
- Register routes in `ui/src/App.tsx`.
- Extend metadata/provider wiring to also fetch and provide `research_collection`.
- Extend the client helper(s) to query Agent Data for the research collection.
