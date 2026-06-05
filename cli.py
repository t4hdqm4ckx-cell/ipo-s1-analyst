"""CLI entry point for the IPO S-1 Analyst Agent."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.table import Table

from agent.fetcher import EDGARFetcher, FilingNotFoundError
from agent.orchestrator import AnalysisError, S1Orchestrator
from agent.reporter import assemble_report, save_report
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, REPORTS_DIR

app = typer.Typer(
    name="s1-analyst",
    help="Agentic IPO S-1 analyst — deep due diligence from SEC filings.",
    add_completion=False,
)
console = Console()


def _validate_env():
    if not ANTHROPIC_API_KEY:
        console.print(
            "[bold red]Error:[/] ANTHROPIC_API_KEY is not set.\n"
            "Copy [cyan].env.example[/] to [cyan].env[/] and add your key.",
            highlight=False,
        )
        raise typer.Exit(1)


@app.command()
def analyze(
    company: str | None = typer.Option(
        None,
        "--company",
        "-c",
        help="Company name to search on SEC EDGAR (e.g. 'SpaceX', 'Klarna').",
    ),
    ticker: str | None = typer.Option(
        None,
        "--ticker",
        "-t",
        help="Ticker symbol (e.g. RDDT, ABNB).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for the report (default: ./reports).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show agent tool calls and reasoning steps.",
    ),
    model: str = typer.Option(
        CLAUDE_MODEL,
        "--model",
        "-m",
        help="Claude model to use.",
    ),
):
    """
    Run a full IPO S-1 due diligence analysis.

    Examples:

        s1-analyst --company "SpaceX"

        s1-analyst --ticker RDDT

        s1-analyst --company "Stripe" --verbose
    """
    if not company and not ticker:
        console.print(
            "[bold red]Error:[/] Provide either --company or --ticker.",
            highlight=False,
        )
        raise typer.Exit(1)

    _validate_env()

    # Override config with CLI flags
    if verbose:
        import config

        config.VERBOSE = True
    if output:
        import config

        config.REPORTS_DIR = output
        output.mkdir(parents=True, exist_ok=True)

    label = ticker.upper() if ticker else company
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]IPO S-1 Analyst[/] — [white]{label}[/]\n"
            f"[dim]Model: {model} | Output: {output or REPORTS_DIR}[/]",
            border_style="cyan",
        )
    )
    console.print()

    # Step 1: Fetch S-1
    filing = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Searching SEC EDGAR for S-1 filing...", total=None)
        try:
            with EDGARFetcher() as fetcher:
                filing = fetcher.find_s1(
                    ticker if ticker else company,
                    is_ticker=bool(ticker),
                )
            progress.update(task, description="S-1 downloaded.")
        except FilingNotFoundError as e:
            console.print(f"\n[bold red]Filing not found:[/] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[bold red]EDGAR error:[/] {e}")
            raise typer.Exit(1)

    console.print(
        f"[green]✓[/] Found: [bold]{filing['company']}[/] "
        f"(filed {filing['filing_date']}, "
        f"{filing['char_count']:,} chars)"
    )
    console.print(f"  [dim]{filing['url']}[/]")
    console.print()

    # Step 2: Run agentic analysis
    findings = None
    tool_summary = ""
    orch = S1Orchestrator(filing)
    # Patch model if overridden via CLI
    if model != CLAUDE_MODEL:
        import config

        config.CLAUDE_MODEL = model

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=not verbose,
    ) as progress:
        task = progress.add_task("Running IB-grade due diligence analysis...", total=None)
        try:
            with orch:
                findings = orch.run()
            findings["_model"] = model
            iterations = orch.iterations
            tool_summary = orch.get_tool_call_summary()
            progress.update(
                task,
                description=f"Analysis complete ({iterations} agent iterations).",
            )
        except AnalysisError as e:
            console.print(f"\n[bold red]Analysis error:[/] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[bold red]Unexpected error:[/] {e}")
            if verbose:
                import traceback

                traceback.print_exc()
            raise typer.Exit(1)

    console.print(
        f"[green]✓[/] Analysis complete — "
        f"{iterations} agent iteration{'s' if iterations != 1 else ''}."
    )
    if verbose and tool_summary:
        console.print(f"  [dim]{tool_summary}[/]")
    console.print()

    # Step 3: Assemble and save report
    report = assemble_report(findings, filing)
    report_path = save_report(report, filing["company"])

    rec = findings.get("investment_recommendation", "HOLD")
    rec_colors = {"BUY": "green", "HOLD": "yellow", "PASS": "red"}
    rec_color = rec_colors.get(rec, "white")

    console.print(Rule(style="dim"))
    console.print()
    console.print(f"  Recommendation: [{rec_color} bold]{rec}[/]")
    console.print(f"  Report saved:   [cyan]{report_path}[/]")
    console.print()

    # Print executive summary preview
    exec_summary = findings.get("executive_summary", "")
    if exec_summary:
        preview = exec_summary[:600] + ("..." if len(exec_summary) > 600 else "")
        console.print(Panel(preview, title="Executive Summary Preview", border_style="dim"))

    console.print()


@app.command(name="recent")
def list_recent(
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of recent S-1 filings to show.",
    ),
):
    """List the most recent S-1 filings on SEC EDGAR."""
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("Fetching recent S-1 filings from EDGAR..."),
        console=console,
        transient=True,
    ) as _:
        with EDGARFetcher() as fetcher:
            filings = fetcher.list_recent_s1s(limit=limit)

    table = Table(title=f"Recent S-1 Filings (last {len(filings)})", border_style="cyan")
    table.add_column("Company", style="bold")
    table.add_column("Filed", style="dim")
    table.add_column("Accession")

    for f in filings:
        table.add_row(f["company"], f["date"], f["accession"])

    console.print(table)
    console.print()
    console.print("[dim]Run: s1-analyst --company <name> to analyze any of these.[/]")
    console.print()


def main():
    app()


if __name__ == "__main__":
    main()
