"""Central configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS: int = int(os.environ.get("MAX_TOKENS", "8096"))

EDGAR_CACHE: bool = os.environ.get("EDGAR_CACHE", "true").lower() == "true"
EDGAR_USER_AGENT: str = os.environ.get(
    "EDGAR_USER_AGENT", "IPO S-1 Analyst kamil7@yahoo.com"
)

REPORTS_DIR: Path = Path(os.environ.get("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR: Path = Path(".cache/edgar")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VERBOSE: bool = os.environ.get("VERBOSE", "false").lower() == "true"

# Maximum characters per S-1 section sent to Claude in a single tool result.
# S-1s can be 2M+ chars; we chunk to stay well within context.
MAX_SECTION_CHARS: int = 120_000

# Max agentic loop iterations before forcing completion
MAX_AGENT_ITERATIONS: int = 25
