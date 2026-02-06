# Deep Research (Planning)

This is a starter for LlamaAgents. See the [LlamaAgents (llamactl) getting started guide](https://developers.llamaindex.ai/python/llamaagents/llamactl/getting-started/) for context on local development and deployment.

To run the application, install [`uv`](https://docs.astral.sh/uv/) and run `uvx llamactl serve`.

## Simple customizations

For basic customizations, update:

- `configs/config.json` under the `research` key (collections + runtime settings)
- workflow events in `src/deep_research/events.py`

## CLI (simulate frontend)

You can interact with the planning workflow from your terminal (simulates frontend
handler creation + event streaming + HITL responses):

```bash
# in one terminal
uvx llamactl serve

# in another terminal
```bash
uv run deep-research plan --query "Compare RAG vs fine-tuning for customer support"
```

If your environment does not resolve `localhost` correctly, pass `127.0.0.1`:

```bash
uv run deep-research plan --base-url http://127.0.0.1:4501 --query "..."
```

If you get a 404, your deployment name may not be `default`. The CLI will try to auto-detect,
but you can also pass it explicitly:

```bash
uv run deep-research plan --deployment deep-research --query "..."
```

To print every raw event:

```bash
uv run deep-research plan --query "..." --print-all-events
```

If the CLI prints "Streaming events..." and then exits immediately, your
workflow server's events endpoint may not be a true SSE stream in your version.
Force polling mode:

```bash
uv run deep-research plan --query "..." --poll
```

## Complex customizations

For more complex customizations, edit the workflows under `src/deep_research/`.

## Linting and type checking

Python and javascript packages contain helpful scripts to lint, format, and type check the code.

To check and fix python code:

```bash
uv run hatch run lint
uv run hatch run typecheck
uv run hatch run test
# run all at once
uv run hatch run all-fix
```

To check and fix javascript code, within the `ui` directory:

```bash
pnpm run lint
pnpm run typecheck
pnpm run test
# run all at once
pnpm run all-fix
```
