# INSTRUCTIONS

## Purpose

`ipo-s1-analyst` is a command-line agent that performs institutional-grade due diligence on IPO S-1 filings using Claude as the analysis engine. It is designed for investors, analysts, and researchers who want a fast, rigorous first-pass on any company going public.

## How to run

### 1. Install dependencies

```bash
pip install -e .
```

Or with a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and set:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run an analysis

```bash
# By company name (searches SEC EDGAR)
s1-analyst --company "SpaceX"

# By ticker symbol
s1-analyst --ticker RDDT

# With verbose agent output (see reasoning steps)
s1-analyst --company "Klarna" --verbose

# Specify output directory
s1-analyst --company "Databricks" --output ./my-reports
```

### 4. Read the report

Reports are saved as Markdown in `reports/` (or your specified output dir):

```
reports/SpaceX_2026-06-04.md
```

## Configuration options (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `MAX_TOKENS` | `8096` | Max tokens per agent response |
| `EDGAR_CACHE` | `true` | Cache downloaded S-1s locally |
| `REPORTS_DIR` | `./reports` | Output directory |
| `VERBOSE` | `false` | Show agent reasoning steps |

## How the agent works

The agent operates in an iterative tool-use loop:

1. **Fetch** — Searches SEC EDGAR for the most recent S-1 filing
2. **Parse** — Splits the document into named sections (Business, MD&A, Risk Factors, Financials, etc.)
3. **Investigate** — Claude reads sections and searches the web in a loop, deciding what to examine next
4. **Conclude** — When sufficiently informed, Claude produces structured findings
5. **Report** — Findings are assembled into a full Markdown report

## Limitations

- Only analyzes S-1 filings (not S-1/A amendments or prospectuses)
- Limited to filings from 2024 onwards (EDGAR full-text search window)
- Web search enrichment depends on DuckDuckGo availability
- Very large S-1s (500+ pages) may hit context limits; the agent will note this
