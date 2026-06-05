"""Tool schemas and implementations for the S-1 analyst agent."""

import json
from typing import Any

from duckduckgo_search import DDGS

from agent.parser import S1Parser
from config import VERBOSE

# ------------------------------------------------------------------
# Tool schemas (passed to Claude API)
# ------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "get_s1_section",
        "description": (
            "Read a specific section of the S-1 filing. Use this to examine "
            "parts of the document you need for your analysis. Call this "
            "multiple times to read different sections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section_name": {
                    "type": "string",
                    "description": (
                        "Section to read. Valid values: "
                        "'summary', 'risk_factors', 'business', 'competition', "
                        "'mda', 'financials', 'use_of_proceeds', 'dilution', "
                        "'capitalization', 'principal_stockholders', "
                        "'management', 'compensation', 'related_party', "
                        "'underwriting', 'notes_to_financials', 'full'. "
                        "Start with 'summary' and 'business' for orientation, "
                        "then drill into specific sections."
                    ),
                }
            },
            "required": ["section_name"],
        },
    },
    {
        "name": "get_financial_table",
        "description": (
            "Extract specific financial tables from the S-1. Use this to get "
            "clean tabular data for revenue, expenses, cash flow, and balance sheet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_type": {
                    "type": "string",
                    "description": (
                        "Type of financial table: "
                        "'income_statement', 'balance_sheet', "
                        "'cash_flow', 'key_metrics'"
                    ),
                }
            },
            "required": ["table_type"],
        },
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for information not in the S-1 — funding rounds, "
            "competitor financials, market size, news, VC investors, analyst views. "
            "Use targeted queries. Results are DuckDuckGo snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1–10, default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_s1_sections",
        "description": (
            "List all sections that were successfully parsed from this S-1. "
            "Call this first if you are unsure what sections are available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "complete_analysis",
        "description": (
            "Signal that your investigation is complete. Call this ONLY when you "
            "have read all the sections you need and have enough information to "
            "write a comprehensive IB-quality due diligence report. Pass your "
            "structured findings — the report will be assembled from these."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "object",
                    "description": "Structured findings from your full investigation.",
                    "properties": {
                        "company_name": {"type": "string"},
                        "filing_date": {"type": "string"},
                        "executive_summary": {"type": "string"},
                        "business_overview": {"type": "string"},
                        "products_and_services": {"type": "string"},
                        "revenue_model": {"type": "string"},
                        "financial_analysis": {"type": "string"},
                        "key_metrics": {"type": "string"},
                        "valuation": {"type": "string"},
                        "comparable_companies": {"type": "string"},
                        "competitive_landscape": {"type": "string"},
                        "moat_analysis": {"type": "string"},
                        "swot": {
                            "type": "object",
                            "properties": {
                                "strengths": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "weaknesses": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "opportunities": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "threats": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                        "funding_history": {"type": "string"},
                        "key_investors": {"type": "string"},
                        "use_of_proceeds": {"type": "string"},
                        "cap_table_summary": {"type": "string"},
                        "risk_flags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "management_assessment": {"type": "string"},
                        "bull_case": {"type": "string"},
                        "base_case": {"type": "string"},
                        "bear_case": {"type": "string"},
                        "investment_recommendation": {
                            "type": "string",
                            "enum": ["BUY", "HOLD", "PASS"],
                        },
                        "recommendation_rationale": {"type": "string"},
                        "key_catalysts": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "key_risks_to_thesis": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "company_name",
                        "executive_summary",
                        "business_overview",
                        "financial_analysis",
                        "valuation",
                        "competitive_landscape",
                        "swot",
                        "investment_recommendation",
                        "recommendation_rationale",
                    ],
                }
            },
            "required": ["findings"],
        },
    },
]


# ------------------------------------------------------------------
# Tool executor
# ------------------------------------------------------------------


class ToolExecutor:
    """Dispatches tool calls to their implementations."""

    def __init__(self, parser: S1Parser):
        self.parser = parser
        self._ddgs = None

    def execute(self, name: str, inputs: dict[str, Any]) -> str:
        if VERBOSE:
            print(f"[tool] {name}({json.dumps(inputs, default=str)[:120]})")

        if name == "get_s1_section":
            return self._get_section(inputs["section_name"])
        elif name == "get_financial_table":
            return self._get_financial_table(inputs["table_type"])
        elif name == "search_web":
            return self._search_web(
                inputs["query"], inputs.get("max_results", 5)
            )
        elif name == "list_s1_sections":
            return self._list_sections()
        elif name == "complete_analysis":
            # Return sentinel — orchestrator handles this
            return "__COMPLETE__"
        else:
            return f"Unknown tool: {name}"

    def get_findings(self, inputs: dict[str, Any]) -> dict:
        """Extract findings from a complete_analysis tool call."""
        return inputs.get("findings", {})

    # ------------------------------------------------------------------
    # Implementations
    # ------------------------------------------------------------------

    def _get_section(self, section_name: str) -> str:
        text = self.parser.get_section(section_name)
        char_count = len(text)
        header = f"[S-1 Section: {section_name} | {char_count:,} chars]\n\n"
        return header + text

    def _get_financial_table(self, table_type: str) -> str:
        text = self.parser.get_financial_table(table_type)
        return f"[Financial Table: {table_type}]\n\n{text}"

    def _search_web(self, query: str, max_results: int = 5) -> str:
        max_results = min(max(1, max_results), 10)
        try:
            if self._ddgs is None:
                self._ddgs = DDGS()
            results = list(self._ddgs.text(query, max_results=max_results))
            if not results:
                return f"No web results found for: {query}"
            lines = [f"[Web Search: '{query}']\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                lines.append(f"{i}. **{title}**\n   {body}\n   {href}\n")
            return "\n".join(lines)
        except Exception as e:
            return f"Web search failed: {e}. Proceed with information from the S-1 only."

    def _list_sections(self) -> str:
        sections = self.parser.list_sections()
        meta = self.parser.get_summary_metadata()
        lines = [
            f"[S-1 Sections for {meta['company']}]",
            f"Document size: {meta['total_chars']:,} chars | "
            f"{meta['table_count']} tables",
            "",
            "Available sections:",
        ]
        for s in sections:
            lines.append(f"  - {s}")
        if not sections:
            lines.append("  (no named sections parsed — try 'full' or 'mda')")
        return "\n".join(lines)

    def close(self):
        if self._ddgs:
            try:
                self._ddgs.close()
            except Exception:
                pass
