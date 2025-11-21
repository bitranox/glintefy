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

from typing import Optional, Sequence

import rich_click as click
from rich.console import Console
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


def main(
    argv: Optional[Sequence[str]] = None,
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
