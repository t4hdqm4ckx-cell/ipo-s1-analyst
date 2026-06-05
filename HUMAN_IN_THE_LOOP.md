# Human in the Loop

## Overview

`ipo-s1-analyst` is an **AI-assisted research tool**, not an autonomous decision-making system. It performs read-only analysis and generates reports for human review. No financial transactions, submissions, or irreversible actions are taken.

## What the agent does autonomously

- Searches SEC EDGAR for S-1 filings
- Downloads and parses filing documents (read-only)
- Performs web searches via DuckDuckGo (read-only)
- Calls the Claude API to generate analysis
- Writes a `.md` report to your local `reports/` directory

## What the agent does NOT do

- Execute trades or financial transactions
- Submit anything to SEC or any authority
- Send emails or messages
- Modify any external systems
- Access authenticated or private data sources

## Human review is required for

- **Investment decisions** — The agent's output is research input, not a trading signal. Always apply your own judgment, risk tolerance, and additional due diligence before investing.
- **Material facts** — Claude can hallucinate or misread complex financial tables. Verify key numbers against the original SEC filing before relying on them.
- **Forward-looking statements** — Bull/bear cases and price targets are illustrative scenarios, not forecasts.

## Data sources used

| Source | Type | Authentication |
|---|---|---|
| SEC EDGAR | Public API | None (rate-limited, respectful UA header) |
| DuckDuckGo Search | Public web | None |
| Anthropic Claude API | LLM inference | Your API key (local env var) |

## Rate limits and costs

- **SEC EDGAR**: Free, ~10 requests/second limit. The agent respects this.
- **DuckDuckGo**: Free, no hard limit. Used sparingly (1-3 queries per analysis).
- **Anthropic API**: Billed per token. A full SpaceX-scale S-1 analysis costs approximately **$0.50–$2.00** depending on filing size and model.

## Transparency

Running with `--verbose` shows every tool call the agent makes, so you can see exactly what it read and searched before drawing conclusions.
