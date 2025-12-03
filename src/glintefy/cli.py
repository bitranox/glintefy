"""CLI adapter wiring the behavior helpers into a rich-click interface.

Purpose
-------
Expose a stable command-line surface using rich-click for consistent,
beautiful terminal output. The CLI delegates to behavior helpers while
maintaining clean separation of concerns.

Contents
--------
* :data:`CLICK_CONTEXT_SETTINGS` - shared Click settings for consistent help.
* :func:`cli` - root command group with global options.
* :func:`cli_info` - print package metadata.
* :func:`cli_hello` - demonstrate success path.
* :func:`cli_fail` - demonstrate error handling.
* :func:`main` - entry point for console scripts.

System Role
-----------
The CLI is the primary adapter for local development workflows. Packaging
targets register the console script defined in __init__conf__. The module
entry point (python -m) reuses the same helpers for consistency.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.markdown import Markdown
from rich.traceback import Traceback
from rich.traceback import install as install_rich_traceback

from . import __init__conf__
from .behaviors import emit_greeting, noop_main, raise_intentional_failure
from .config import get_config

#: Shared Click context flags for consistent help output.
CLICK_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

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
    default=False,
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
# Config Commands
# =============================================================================


@cli.command("config-deploy", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--target",
    "targets",
    type=click.Choice(["app", "host", "user"], case_sensitive=False),
    multiple=True,
    required=True,
    help="Target configuration layer(s) to deploy to (can specify multiple)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing configuration files",
)
def cli_config_deploy(targets: tuple[str, ...], force: bool) -> None:
    """Deploy default configuration to system or user directories.

    Creates configuration files in platform-specific locations:

    \b
    - app:  System-wide application config (requires privileges)
    - host: System-wide host config (requires privileges)
    - user: User-specific config (~/.config on Linux)

    By default, existing files are not overwritten. Use --force to overwrite.

    Examples:

    \b
    # Deploy to user config directory
    $ python -m glintefy config-deploy --target user

    \b
    # Deploy to both app and user directories
    $ python -m glintefy config-deploy --target app --target user

    \b
    # Force overwrite existing config
    $ python -m glintefy config-deploy --target user --force
    """
    from .config_deploy import deploy_configuration

    try:
        deployed_paths = deploy_configuration(targets=list(targets), force=force)

        if deployed_paths:
            console.print("\n[green]Configuration deployed successfully:[/green]")
            for path in deployed_paths:
                console.print(f"  [green][OK][/green] {path}")
        else:
            console.print("\n[yellow]No files were created (all target files already exist).[/yellow]")
            console.print("Use --force to overwrite existing configuration files.")

    except PermissionError as exc:
        console.print(f"\n[red]Error: Permission denied. {exc}[/red]")
        console.print("[dim]Hint: System-wide deployment (--target app/host) may require sudo.[/dim]")
        raise SystemExit(1) from exc
    except Exception as exc:
        console.print(f"\n[red]Error: Failed to deploy configuration: {exc}[/red]")
        raise SystemExit(1) from exc


@cli.command("config-show", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--section",
    "-s",
    default=None,
    help="Show only specific section (e.g., 'review.quality', 'general.timeouts')",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON instead of TOML-like format",
)
def cli_config_show(section: str | None, as_json: bool) -> None:
    """Show current effective configuration.

    Displays the merged configuration from all sources:
    package defaults, user config, project config, and environment variables.

    Examples:

    \b
    $ python -m glintefy config-show
    $ python -m glintefy config-show -s review.quality
    $ python -m glintefy config-show --json
    """
    import json

    from .config import get_config, get_section

    if section:
        data = get_section(section)
        if not data:
            console.print(f"[yellow]Section '{section}' not found or empty[/yellow]")
            return
    else:
        config = get_config()
        data = dict(config)

    if as_json:
        console.print(json.dumps(data, indent=2, default=str))
    else:
        _print_config_toml(data)


@cli.command("config-path", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_config_path() -> None:
    """Show paths where config files are loaded from.

    Displays all configuration file locations and their status:
    - Package defaults (always exists)
    - User config (platform-specific)
    - Project config
    - Environment variable prefix
    """
    from platformdirs import user_config_dir

    from .__init__conf__ import LAYEREDCONF_SLUG, LAYEREDCONF_VENDOR
    from .config import _DEFAULT_CONFIG_FILE

    # Get platform-specific paths
    user_dir = Path(user_config_dir(LAYEREDCONF_SLUG, LAYEREDCONF_VENDOR))
    user_config = user_dir / "config.toml"
    project_config = Path.cwd() / f".{LAYEREDCONF_SLUG}.toml"
    pyproject = Path.cwd() / "pyproject.toml"

    console.print("[bold]Configuration file locations:[/bold]\n")

    # Package defaults
    status = "[green][EXISTS][/green]" if _DEFAULT_CONFIG_FILE.exists() else "[red][MISSING][/red]"
    console.print(f"  {status} Package defaults: {_DEFAULT_CONFIG_FILE}")

    # User config
    status = "[green][EXISTS][/green]" if user_config.exists() else "[dim][MISSING][/dim]"
    console.print(f"  {status} User config: {user_config}")

    # Project config
    status = "[green][EXISTS][/green]" if project_config.exists() else "[dim][MISSING][/dim]"
    console.print(f"  {status} Project config: {project_config}")

    # pyproject.toml
    console.print(f"  pyproject.toml: {pyproject}")
    console.print(f"    (use [tool.{LAYEREDCONF_SLUG}] section)")

    # Environment variable prefix
    env_prefix = f"{LAYEREDCONF_SLUG.upper()}___"
    console.print("\n[bold]Environment variable prefix:[/bold]")
    console.print(f"  {env_prefix}<SECTION>__<KEY>=<VALUE>")
    console.print(f"\n  Example: {env_prefix}GENERAL__LOG_LEVEL=DEBUG")


def _print_config_toml(data: dict, prefix: str = "") -> None:
    """Print configuration in TOML-like format."""
    for key, value in data.items():
        if isinstance(value, dict):
            _print_config_toml(value, prefix=f"{prefix}{key}.")
        else:
            # Format value based on type
            if isinstance(value, bool):
                val_str = "true" if value else "false"
            elif isinstance(value, str):
                val_str = f'"{value}"'
            elif isinstance(value, list):
                val_str = str(value)
            else:
                val_str = str(value)
            console.print(f"{prefix}{key} = {val_str}")


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
    help="Scan mode: 'git' for uncommitted changes (default), 'full' for all files",
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

    The profiling wraps your command with cProfile to capture function-level
    timing data. This data is then used by the cache subserver to identify
    which functions are called frequently and would benefit from caching.

    Examples:
        python -m glintefy review profile -- python my_app.py
        python -m glintefy review profile -- pytest tests/
        python -m glintefy review profile -- python -m my_module
    """
    import subprocess
    import sys

    repo_path = ctx.obj["repo_path"]

    # Get output directory from config
    config = get_config(start_dir=str(repo_path))
    review_output_dir = config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")
    output_dir = repo_path / review_output_dir / "perf"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_profile.prof"

    console.print(f"[bold cyan]Profiling:[/bold cyan] {' '.join(command)}")
    console.print(f"[dim]Output will be saved to: {output_path}[/dim]\n")

    # Build the profiled command
    # If command starts with 'python', replace with profiled version
    # Otherwise wrap with python -m cProfile
    cmd_list = list(command)

    if cmd_list[0] in ("python", "python3", sys.executable):
        # Replace python with profiled version: python -m cProfile -o output ...rest
        profiled_cmd = [cmd_list[0], "-m", "cProfile", "-o", str(output_path)] + cmd_list[1:]
    elif cmd_list[0] == "pytest":
        # pytest is often run directly, wrap it
        profiled_cmd = [sys.executable, "-m", "cProfile", "-o", str(output_path), "-m", "pytest"] + cmd_list[1:]
    else:
        # For other commands, try wrapping with python -m cProfile -m
        # This works for modules (e.g., `mymodule` -> `python -m cProfile -m mymodule`)
        profiled_cmd = [sys.executable, "-m", "cProfile", "-o", str(output_path), "-m"] + cmd_list

    console.print(f"[dim]Running: {' '.join(profiled_cmd)}[/dim]\n")

    try:
        result = subprocess.run(
            profiled_cmd,
            check=False,
            cwd=repo_path,
            capture_output=False,
        )
        exit_code = result.returncode
    except Exception as e:
        console.print(f"[red]Error running command: {e}[/red]")
        exit_code = 1

    # Check if profile was created
    if output_path.exists():
        if exit_code == 0:
            console.print("\n[green][OK][/green] Profiling complete")
        else:
            console.print(f"\n[yellow][WARN][/yellow] Command exited with code {exit_code}, but profiling data saved")

        console.print(f"[green][OK][/green] Profile saved to: {output_path}")
        console.print("\n[bold]Next step:[/bold]")
        console.print("  python -m glintefy review cache")
    else:
        console.print("\n[red][FAIL][/red] Profiling failed - no profile data generated")
        console.print("[dim]Make sure the command is a Python script or module[/dim]")


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
    help="Scan mode: 'git' for uncommitted changes (default), 'full' for all files",
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
            console.print(f"  - {error}")

    # Print individual results
    for name in ["scope", "quality", "security", "deps", "docs", "perf", "report"]:
        sub_result = result.get(name)
        if sub_result:
            sub_status = sub_result.get("status", "N/A")
            console.print(f"\n[bold]{name.title()}[/]: {sub_status}")


@review_group.command("clean", context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    "--subserver",
    "-s",
    type=click.Choice(["all", "scope", "quality", "security", "deps", "docs", "perf", "cache", "report", "profile"]),
    default="all",
    help="Clean specific subserver output (default: all)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
@click.pass_context
def review_clean(ctx: click.Context, subserver: str, dry_run: bool) -> None:
    """Clean analysis output files and cached data.

    Remove old analysis results, profile data, and cached files
    to start fresh or free up disk space.

    Examples:
        python -m glintefy review clean              # Clean all
        python -m glintefy review clean -s profile   # Clean profile data only
        python -m glintefy review clean -s cache     # Clean cache analysis only
        python -m glintefy review clean --dry-run    # Show what would be deleted
    """
    import shutil

    repo_path = ctx.obj["repo_path"]

    # Get output directory from config
    config = get_config(start_dir=str(repo_path))
    review_output_dir = config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")
    base_dir = repo_path / review_output_dir

    # Map subserver names to directories
    subserver_dirs = {
        "scope": base_dir / "scope",
        "quality": base_dir / "quality",
        "security": base_dir / "security",
        "deps": base_dir / "deps",
        "docs": base_dir / "docs",
        "perf": base_dir / "perf",
        "cache": base_dir / "cache",
        "report": base_dir / "report",
        "profile": base_dir / "perf" / "test_profile.prof",  # Special case: just the profile file
    }

    if subserver == "all":
        targets = [base_dir]
        target_names = ["all review data"]
    elif subserver == "profile":
        # Special handling for profile - just the .prof file
        targets = [subserver_dirs["profile"]]
        target_names = ["profile data"]
    else:
        targets = [subserver_dirs[subserver]]
        target_names = [f"{subserver} data"]

    deleted_count = 0
    total_size = 0

    for target, name in zip(targets, target_names):
        if not target.exists():
            console.print(f"[dim]No {name} found at {target}[/dim]")
            continue

        # Calculate size
        if target.is_file():
            size = target.stat().st_size
            total_size += size
            size_str = _format_size(size)

            if dry_run:
                console.print(f"[yellow]Would delete:[/yellow] {target} ({size_str})")
            else:
                target.unlink()
                console.print(f"[green][OK][/green] Deleted {target} ({size_str})")
                deleted_count += 1
        else:
            # Directory
            size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            total_size += size
            size_str = _format_size(size)
            file_count = sum(1 for f in target.rglob("*") if f.is_file())

            if dry_run:
                console.print(f"[yellow]Would delete:[/yellow] {target}/ ({file_count} files, {size_str})")
            else:
                shutil.rmtree(target)
                console.print(f"[green][OK][/green] Deleted {target}/ ({file_count} files, {size_str})")
                deleted_count += 1

    # Summary
    if dry_run:
        console.print(f"\n[bold]Dry run complete.[/bold] Would free {_format_size(total_size)}")
    elif deleted_count > 0:
        console.print(f"\n[bold green]Cleanup complete.[/bold green] Freed {_format_size(total_size)}")
    else:
        console.print("\n[dim]Nothing to clean.[/dim]")


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


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
            console.print(f"  - {error}")


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
