"""Agentic orchestrator — drives the Claude tool-use loop for S-1 analysis."""

from pathlib import Path

import anthropic

from agent.analyzer import build_context_summary
from agent.parser import S1Parser
from agent.tools import TOOL_SCHEMAS, ToolExecutor
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_AGENT_ITERATIONS, MAX_TOKENS, VERBOSE

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.md"


class AnalysisError(Exception):
    pass


class S1Orchestrator:
    """
    Runs the agentic investigation loop:
      1. Provides Claude with S-1 metadata + tools
      2. Processes tool calls until Claude calls complete_analysis
      3. Returns structured findings dict
    """

    def __init__(self, filing: dict):
        self.filing = filing
        self.parser = S1Parser(filing["content"], filing["company"])
        self.executor = ToolExecutor(self.parser)
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._system_prompt = self._build_system_prompt()
        self.findings: dict | None = None
        self.iterations = 0
        self.tool_call_log: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Execute the full investigation loop and return findings dict."""
        messages = self._build_initial_messages()

        for i in range(MAX_AGENT_ITERATIONS):
            self.iterations = i + 1
            if VERBOSE:
                print(f"\n[orchestrator] Iteration {self.iterations}")

            response = self._call_claude(messages)

            if VERBOSE:
                self._log_response_summary(response)

            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "end_turn" or not tool_blocks:
                if not self.findings:
                    raise AnalysisError(
                        "Agent stopped without calling complete_analysis. "
                        "Try increasing MAX_AGENT_ITERATIONS or check your API key."
                    )
                break

            # Process tool calls
            tool_results = []

            for block in tool_blocks:
                result = self.executor.execute(block.name, block.input)

                self.tool_call_log.append(
                    {"iteration": self.iterations, "tool": block.name, "result_len": len(result)}
                )

                if result == "__COMPLETE__":
                    self.findings = self.executor.get_findings(block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Analysis complete. Report will be generated.",
                        }
                    )
                else:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "assistant", "content": response.content})

            if self.findings:
                messages.append({"role": "user", "content": tool_results})
                break

            messages.append({"role": "user", "content": tool_results})

        if not self.findings:
            raise AnalysisError(
                f"No findings after {self.iterations} iterations. "
                "The agent did not reach a conclusion."
            )

        return self.findings

    def get_tool_call_summary(self) -> str:
        """Human-readable summary of all tool calls made during analysis."""
        if not self.tool_call_log:
            return "No tool calls recorded."
        lines = [f"Tool calls made ({len(self.tool_call_log)} total):"]
        for entry in self.tool_call_log:
            lines.append(
                f"  Iter {entry['iteration']:2d}: {entry['tool']:<25} "
                f"({entry['result_len']:,} chars returned)"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Message building
    # ------------------------------------------------------------------

    def _build_initial_messages(self) -> list[dict]:
        meta = self.parser.get_summary_metadata()
        pre_scan = build_context_summary(self.parser, self.filing)
        intro = (
            f"You are analyzing the S-1 filing for **{self.filing['company']}**.\n\n"
            f"Filing date: {self.filing['filing_date']}\n"
            f"Document size: {meta['total_chars']:,} characters, {meta['table_count']} tables\n"
            f"EDGAR URL: {self.filing['url']}\n\n"
            f"{pre_scan}\n\n"
            "---\n\n"
            "Begin your investigation. Start with `list_s1_sections` to orient yourself, "
            "then systematically work through the filing. Be thorough — this is an "
            "institutional-grade analysis. When you have enough information, call "
            "`complete_analysis` with your full structured findings."
        )
        return [{"role": "user", "content": intro}]

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Claude API call with prompt caching
    # ------------------------------------------------------------------

    def _call_claude(self, messages: list[dict]) -> anthropic.types.Message:
        """Call Claude with tool use enabled and prompt caching on system."""
        system_with_cache = [
            {
                "type": "text",
                "text": self._system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        return self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=system_with_cache,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_response_summary(self, response: anthropic.types.Message):
        text_count = sum(1 for b in response.content if b.type == "text")
        tool_count = sum(1 for b in response.content if b.type == "tool_use")
        tool_names = [b.name for b in response.content if b.type == "tool_use"]
        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_create = getattr(usage, "cache_creation_input_tokens", 0)
        print(
            f"  stop_reason={response.stop_reason} | "
            f"text={text_count} tools={tool_count} {tool_names} | "
            f"in={usage.input_tokens} out={usage.output_tokens} | "
            f"cache_read={cache_read} cache_create={cache_create}"
        )

    def close(self):
        self.executor.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
