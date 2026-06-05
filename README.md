# IPO S-1 Analyst Agent

An agentic AI analyst that reads SEC S-1 filings and produces institutional-grade due diligence reports — the way a seasoned IB analyst would.

## What it does

Given a company name or ticker, the agent:

1. Fetches the most recent S-1 from SEC EDGAR (no API key needed)
2. Parses the filing into structured sections
3. Runs an **agentic investigation loop** powered by Claude — reading sections, searching the web for enrichment, and iterating until it has enough to conclude
4. Produces a comprehensive `.md` report covering:
   - Business overview and product analysis
   - Financial deep-dive (revenue, burn, margins, growth)
   - Valuation with comparable companies
   - Competitive landscape
   - SWOT analysis
   - Funding history and VC/backer roster
   - Red flags from Risk Factors
   - Use of proceeds and cap table
   - **Investment conclusion** — BUY / HOLD / PASS with bull/base/bear cases

## Quick start

```bash
# Install
pip install -e .

# Set your Anthropic API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Analyze a company by name
s1-analyst --company "SpaceX"

# Analyze by ticker
s1-analyst --ticker RDDT

# Verbose mode (shows agent's reasoning steps)
s1-analyst --company "Stripe" --verbose
```

## Output

Reports are saved to `reports/{CompanyName}_{date}.md`.

Example structure:
```
reports/
  SpaceX_2026-06-04.md
  Reddit_2026-06-04.md
```

## Architecture

```
agent/
  fetcher.py      — SEC EDGAR search + S-1 download + local caching
  parser.py       — Section extraction, chunking, financial table parsing
  analyzer.py     — Pre-scan: extract financial signals before agent loop
  valuation.py    — EV/Revenue, gross margin, Rule of 40, burn multiple, sector comps
  risk_scorer.py  — 20-signal risk scanner → score + LOW/MEDIUM/HIGH/CRITICAL rating
  tools.py        — Claude tool schemas: get_section, search_web, search_filing, IPO price, etc.
  orchestrator.py — Agentic loop: Claude iterates with tools until complete
  reporter.py     — Markdown report assembly with risk badge + file output
prompts/
  system_prompt.md   — IB analyst persona and investigation instructions
  report_template.md — Output format specification
examples/
  spacex_analysis.md — SpaceX-specific guidance and filing notes
cli.py            — Typer CLI (analyze + recent subcommands)
config.py         — Environment variable configuration
tests/            — 69 unit + integration tests (zero network calls)
```

## Requirements

- Python 3.11+
- Anthropic API key ([get one here](https://console.anthropic.com))
- Internet access (SEC EDGAR + DuckDuckGo web search)

## Notes

- S-1 documents are cached locally in `.cache/edgar/` after first download
- The agent uses **prompt caching** to minimize API costs on large filings
- A **pre-scan** runs before the agent loop: financial signals, risk score (20 patterns), and sector comps are injected into the first message
- Analysis depth scales with filing size — SpaceX-scale filings take ~3-5 minutes
- The automated risk scorer flags 20 patterns (going concern, material weakness, dual-class, export controls, etc.) and outputs a 0–100 score + LOW/MEDIUM/HIGH/CRITICAL rating
- This tool performs **read-only** operations — it never submits anything
- **69 unit and integration tests**, all passing, zero network calls in the test suite

## Disclaimer

This tool is for informational and research purposes only. Nothing in its output constitutes investment advice. Always do your own due diligence.

## License

MIT
