# CLAUDE.md — IPO S-1 Analyst Agent

## Project Overview

An agentic AI system that performs institutional-grade IPO due diligence by reading SEC S-1 filings and producing investment analyst-quality Markdown reports.

## Key Architecture Decisions

- **Agentic loop** — Claude calls tools iteratively (read section → search web → read more) until it has enough to conclude. Not a simple pipeline.
- **Pre-scan module** — `agent/analyzer.py` extracts financial signals before the loop starts, seeding Claude with numbers so it doesn't waste iterations on orientation.
- **Prompt caching** — System prompt is cached with `cache_control: ephemeral` to reduce cost on multi-iteration analyses of large S-1s.
- **Section-based chunking** — S-1s can be 2M+ characters. The parser slices by named sections; each tool call returns ≤120k chars.
- **`complete_analysis` as terminator** — The agent signals completion by calling this tool with structured findings. The orchestrator detects it and exits the loop.

## Development Setup

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env  # add ANTHROPIC_API_KEY
```

## Running Tests

```bash
.venv/bin/pytest tests/ -v
```

All tests are unit tests (no API calls, no network). `tests/fixtures/sample_s1_excerpt.html` is the mock S-1 used across tests.

## Module Map

| File | Role |
|---|---|
| `agent/fetcher.py` | EDGAR search + S-1 download + local cache |
| `agent/parser.py` | HTML section extraction + financial table parsing |
| `agent/analyzer.py` | Pre-scan: extract signals before agentic loop |
| `agent/tools.py` | Tool schemas + executor (dispatches to parser/web) |
| `agent/orchestrator.py` | Agentic loop: iterates with Claude until `complete_analysis` |
| `agent/reporter.py` | Assembles findings → Markdown report + saves to disk |
| `cli.py` | Typer CLI entry point with Rich progress UI |
| `config.py` | All env var config in one place |
| `prompts/system_prompt.md` | IB analyst persona + investigation instructions |

## Adding New Tools

1. Add schema to `TOOL_SCHEMAS` list in `agent/tools.py`
2. Add `elif name == "your_tool":` branch in `ToolExecutor.execute()`
3. Implement the method on `ToolExecutor`
4. Update `system_prompt.md` if the tool changes investigation strategy

## Code Style

- ruff for linting (`ruff check .` / `ruff format .`)
- No comments unless the WHY is non-obvious
- Type hints on all public methods
