"""CLI adapter wiring the behavior helpers into a rich-click interface.

Purpose
-------
Expose a stable command-line surface using rich-click for consistent,
beautiful terminal output. The CLI delegates to behavior helpers while
maintaining clean separation of concerns.

Contents
--------
* :data:`CLICK_CONTEXT_SETTINGS` – shared Click settings for consistent help.
* :func:`cli` – root command group with global options.
* :func:`cli_info` – print package metadata.
* :func:`cli_hello` – demonstrate success path.
* :func:`cli_fail` – demonstrate error handling.
* :func:`main` – entry point for console scripts.

System Role
-----------
The CLI is the primary adapter for local development workflows. Packaging
targets register the console script defined in __init__conf__. The module
entry point (python -m) reuses the same helpers for consistency.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import rich_click as click
from rich.console import Console
from rich.markdown import Markdown
from rich.traceback import Traceback, install as install_rich_traceback

from . import __init__conf__
from .behaviors import emit_greeting, noop_main, raise_intentional_failure

#: Shared Click context flags for consistent help output.
CLICK_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}  # noqa: C408

#: Console for rich output
console = Console()


@click.group(
    help=__init__conf__.title,
    context_settings=CLICK_CONTEXT_SETTINGS,
    invoke_without_command=True,
)
@click.version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@click.option(
    "--traceback/--no-traceback",
    is_flag=True,
    default=True,
    help="Show full Python traceback on errors (default: enabled)",
)
@click.pass_context
def cli(ctx: click.Context, traceback: bool) -> None:
    """Root command storing global flags.

    When invoked without a subcommand, displays help unless --traceback
    is explicitly provided (for backward compatibility).

    Examples
    --------
    >>> from click.testing import CliRunner
    >>> runner = CliRunner()
    >>> result = runner.invoke(cli, ["hello"])
    >>> result.exit_code
    0
    >>> "Hello World" in result.output
    True
    """
    # Store traceback preference in context
    ctx.ensure_object(dict)
    ctx.obj["traceback"] = traceback

    # Show help if no subcommand and no explicit option
    if ctx.invoked_subcommand is None:
        # Check if traceback flag was explicitly provided
        from click.core import ParameterSource

        source = ctx.get_parameter_source("traceback")
        if source not in (ParameterSource.DEFAULT, None):
            # Traceback was explicitly set, run default behavior
            noop_main()
        else:
            # No subcommand and default traceback value, show help
            click.echo(ctx.get_help())


@cli.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Print resolved metadata so users can inspect installation details."""
    __init__conf__.print_info()


@cli.command("hello", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_hello() -> None:
    """Demonstrate the success path by emitting the canonical greeting."""
    emit_greeting()


@cli.command("fail", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_fail() -> None:
    """Trigger the intentional failure helper to test error handling."""
    raise_intentional_failure()


# =============================================================================
# Review Commands
# =============================================================================


@cli.group("review", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repository path (default: current directory)",
)
@click.pass_context
def review_group(ctx: click.Context, repo: Path | None) -> None:
    """Code review and analysis commands.

    Run various code analysis tools including scope detection,
    quality analysis, security scanning, and more.
    """
    ctx.ensure_object(dict)
    ctx.obj["repo_path"] = repo or Path.cwd()


@review_group.command("scope", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["git", "full"]),
    default="git",
    help="Scan mode: 'git' for uncommitted changes, 'full' for all files",
)
@click.pass_context
def review_scope(ctx: click.Context, mode: str) -> None:
    """Determine which files need to be reviewed."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_scope(mode=mode)

    _print_review_result(result)


@review_group.command("quality", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--complexity",
    "-c",
    type=int,
    default=None,
    help="Maximum cyclomatic complexity threshold (default: 10)",
)
@click.option(
    "--maintainability",
    "-m",
    type=int,
    default=None,
    help="Minimum maintainability index (default: 20)",
)
@click.pass_context
def review_quality(ctx: click.Context, complexity: int | None, maintainability: int | None) -> None:
    """Analyze code quality including complexity and maintainability."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_quality(
        complexity_threshold=complexity,
        maintainability_threshold=maintainability,
    )

    _print_review_result(result)


@review_group.command("security", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["low", "medium", "high"]),
    default="low",
    help="Minimum severity to report",
)
@click.option(
    "--confidence",
    "-c",
    type=click.Choice(["low", "medium", "high"]),
    default="low",
    help="Minimum confidence to report",
)
@click.pass_context
def review_security(ctx: click.Context, severity: str, confidence: str) -> None:
    """Scan code for security vulnerabilities using Bandit."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_security(
        severity_threshold=severity,
        confidence_threshold=confidence,
    )

    _print_review_result(result)


@review_group.command("deps", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--no-vulnerabilities",
    is_flag=True,
    help="Skip vulnerability scanning",
)
@click.option(
    "--no-licenses",
    is_flag=True,
    help="Skip license compliance checking",
)
@click.option(
    "--no-outdated",
    is_flag=True,
    help="Skip outdated package detection",
)
@click.pass_context
def review_deps(
    ctx: click.Context,
    no_vulnerabilities: bool,
    no_licenses: bool,
    no_outdated: bool,
) -> None:
    """Analyze project dependencies for vulnerabilities and compliance."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_deps(
        scan_vulnerabilities=not no_vulnerabilities,
        check_licenses=not no_licenses,
        check_outdated=not no_outdated,
    )

    _print_review_result(result)


@review_group.command("docs", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--min-coverage",
    "-c",
    type=int,
    default=None,
    help="Minimum docstring coverage percentage (default: 80)",
)
@click.pass_context
def review_docs(ctx: click.Context, min_coverage: int | None) -> None:
    """Analyze documentation coverage and quality."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_docs(min_coverage=min_coverage)

    _print_review_result(result)


@review_group.command("perf", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--no-profiling",
    is_flag=True,
    help="Skip test profiling",
)
@click.pass_context
def review_perf(ctx: click.Context, no_profiling: bool) -> None:
    """Analyze code for performance issues and patterns."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_perf(run_profiling=not no_profiling)

    _print_review_result(result)


@review_group.command("profile", context_settings=CLICK_CONTEXT_SETTINGS)
@click.argument("command", nargs=-1, required=True)
@click.pass_context
def review_profile(ctx: click.Context, command: tuple[str, ...]) -> None:
    """Profile a command and save data for cache analysis.

    Examples:
        python -m btx_fix_mcp review profile -- python my_app.py
        python -m btx_fix_mcp review profile -- pytest tests/
        python -m btx_fix_mcp review profile -- python -m my_module
    """
    import cProfile
    import subprocess
    from pathlib import Path

    repo_path = ctx.obj["repo_path"]

    # Create profiling output directory
    output_dir = repo_path / "LLM-CONTEXT" / "btx_fix_mcp" / "review" / "perf"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_profile.prof"

    console.print(f"[bold cyan]Profiling:[/bold cyan] {' '.join(command)}")
    console.print(f"[dim]Output will be saved to: {output_path}[/dim]\n")

    # Run command with profiling
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        result = subprocess.run(
            list(command),
            cwd=repo_path,
            capture_output=False,
        )
        exit_code = result.returncode
    except Exception as e:
        console.print(f"[red]Error running command: {e}[/red]")
        exit_code = 1
    finally:
        profiler.disable()
        profiler.dump_stats(output_path)

    if exit_code == 0:
        console.print(f"\n[green]✓[/green] Profiling complete")
    else:
        console.print(f"\n[yellow]⚠[/yellow] Command exited with code {exit_code}, but profiling data saved")

    console.print(f"[green]✓[/green] Profile saved to: {output_path}")
    console.print("\n[bold]Next step:[/bold]")
    console.print("  python -m btx_fix_mcp review cache")


@review_group.command("cache", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--cache-size",
    type=int,
    default=128,
    help="LRU cache size for testing (default: 128)",
)
@click.option(
    "--hit-rate",
    type=float,
    default=20.0,
    help="Minimum cache hit rate threshold (default: 20.0%)",
)
@click.option(
    "--speedup",
    type=float,
    default=5.0,
    help="Minimum speedup threshold (default: 5.0%)",
)
@click.pass_context
def review_cache(ctx: click.Context, cache_size: int, hit_rate: float, speedup: float) -> None:
    """Analyze caching opportunities and evaluate existing caches."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_cache(
        cache_size=cache_size,
        hit_rate_threshold=hit_rate,
        speedup_threshold=speedup,
    )

    _print_review_result(result)


@review_group.command("report", context_settings=CLICK_CONTEXT_SETTINGS)
@click.pass_context
def review_report(ctx: click.Context) -> None:
    """Generate consolidated report from all analysis results."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_report()

    _print_review_result(result)


@review_group.command("all", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["git", "full"]),
    default="git",
    help="Scan mode for scope analysis",
)
@click.option(
    "--complexity",
    type=int,
    default=None,
    help="Maximum cyclomatic complexity threshold",
)
@click.option(
    "--severity",
    type=click.Choice(["low", "medium", "high"]),
    default="low",
    help="Minimum security severity to report",
)
@click.pass_context
def review_all(ctx: click.Context, mode: str, complexity: int | None, severity: str) -> None:
    """Run complete code review (all sub-servers)."""
    from .servers.review import ReviewMCPServer

    repo_path = ctx.obj["repo_path"]
    server = ReviewMCPServer(repo_path=repo_path)
    result = server.run_all(
        mode=mode,
        complexity_threshold=complexity,
        severity_threshold=severity,
    )

    # Print overall status
    status = result.get("overall_status", "UNKNOWN")
    status_color = {
        "SUCCESS": "green",
        "PARTIAL": "yellow",
        "FAILED": "red",
    }.get(status, "white")

    console.print(f"\n[bold {status_color}]Overall Status: {status}[/]")

    if result.get("errors"):
        console.print("\n[red]Errors:[/]")
        for error in result["errors"]:
            console.print(f"  • {error}")

    # Print individual results
    for name in ["scope", "quality", "security", "deps", "docs", "perf", "report"]:
        sub_result = result.get(name)
        if sub_result:
            sub_status = sub_result.get("status", "N/A")
            console.print(f"\n[bold]{name.title()}[/]: {sub_status}")


def _print_review_result(result: dict) -> None:
    """Print a review result with rich formatting."""
    status = result.get("status", "UNKNOWN")
    status_color = {
        "SUCCESS": "green",
        "PARTIAL": "yellow",
        "FAILED": "red",
    }.get(status, "white")

    console.print(f"\n[bold {status_color}]Status: {status}[/]")

    # Print summary as markdown
    summary = result.get("summary", "")
    if summary:
        console.print(Markdown(summary))

    # Print metrics
    metrics = result.get("metrics", {})
    if metrics:
        console.print("\n[bold]Metrics:[/]")
        for key, value in metrics.items():
            console.print(f"  {key}: {value}")

    # Print errors if any
    errors = result.get("errors", [])
    if errors:
        console.print("\n[red]Errors:[/]")
        for error in errors:
            console.print(f"  • {error}")


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Execute the CLI and return the exit code.

    This is the entry point used by console scripts and python -m execution.

    Parameters
    ----------
    argv:
        Optional sequence of CLI arguments. None uses sys.argv.

    Returns
    -------
    int
        Exit code: 0 for success, non-zero for errors.

    Examples
    --------
    >>> main(["hello"])
    Hello World
    0
    """
    # Check if --no-traceback flag is in arguments (default is to show traceback)
    import sys as _sys

    argv_list = list(argv) if argv else _sys.argv[1:]
    show_traceback = "--no-traceback" not in argv_list

    # Install rich traceback with locals if requested
    if show_traceback:
        install_rich_traceback(show_locals=True)

    try:
        # Use standalone_mode=False to catch exceptions ourselves
        cli(args=argv, standalone_mode=False, prog_name=__init__conf__.shell_command)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (1 if e.code else 0)
    except Exception as exc:
        if show_traceback:
            # Show full rich traceback with locals
            tb = Traceback.from_exception(
                type(exc),
                exc,
                exc.__traceback__,
                show_locals=True,
                width=120,
            )
            console.print(tb)
        else:
            # Show simple error message without traceback
            from rich.style import Style

            error_style = Style(color="red", bold=True)
            console.print(f"Error: {type(exc).__name__}: {exc}", style=error_style)
        return 1
