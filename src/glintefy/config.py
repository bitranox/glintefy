"""Configuration loading using lib_layered_config.

Purpose
-------
Provide a centralized configuration loader that reads settings from:
1. Package defaults (defaultconfig.toml)
2. User config (~/.config/glintefy/config.toml on Linux)
3. Project config (.glintefy.yaml or .glintefy.yaml)
4. Environment variables (GLINTEFY___<SECTION>__<KEY>=<VALUE>)

Environment Variable Format
---------------------------
- Triple underscore (___) separates prefix from section
- Double underscore (__) separates section from key
- Example: GLINTEFY___GENERAL__LOG_LEVEL=DEBUG
- Example: GLINTEFY___REVIEW__QUALITY__COMPLEXITY_THRESHOLD=15

Contents
--------
* :func:`get_config` - Load merged configuration
* :func:`get_section` - Get a specific config section (cached)
* :func:`get_review_config` - Get review sub-server configuration (cached)
* :func:`get_fix_config` - Get fix sub-server configuration

System Role
-----------
Acts as the configuration adapter layer, abstracting lib_layered_config
details from sub-servers and orchestrators.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib_layered_config import Config, read_config

from glintefy.__init__conf__ import (
    LAYEREDCONF_APP,
    LAYEREDCONF_SLUG,
    LAYEREDCONF_VENDOR,
)

# Path to the default configuration file bundled with the package
_DEFAULT_CONFIG_FILE = Path(__file__).parent / "defaultconfig.toml"

# Cached config instance
_cached_config: Config | None = None


def get_config(
    start_dir: str | None = None,
    reload: bool = False,
) -> Config:
    """Load the merged configuration from all layers.

    Parameters
    ----------
    start_dir:
        Directory to start searching for project config files.
        Defaults to current working directory.
    reload:
        If True, bypass cache and reload configuration.

    Returns
    -------
    Config
        Immutable configuration with provenance metadata.

    Examples
    --------
    >>> config = get_config()
    >>> isinstance(config, Config)
    True
    """
    global _cached_config

    if _cached_config is not None and not reload:
        return _cached_config

    _cached_config = read_config(
        vendor=LAYEREDCONF_VENDOR,
        app=LAYEREDCONF_APP,
        slug=LAYEREDCONF_SLUG,
        prefer=["toml", "yaml", "json"],
        start_dir=start_dir or str(Path.cwd()),
        default_file=_DEFAULT_CONFIG_FILE,
    )

    return _cached_config


def get_section(section: str, start_dir: str | None = None) -> dict[str, Any]:
    """Get a specific configuration section.

    Parameters
    ----------
    section:
        Dotted path to the section (e.g., "review.quality", "tools.bandit").
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    dict
        Configuration values for the section, or empty dict if not found.

    Examples
    --------
    >>> quality_config = get_section("review.quality")
    >>> isinstance(quality_config, dict)
    True
    """
    config = get_config(start_dir=start_dir)

    # Navigate through dotted path
    parts = section.split(".")
    current: Any = dict(config)

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return {}

    return current if isinstance(current, dict) else {}


def get_review_config(
    subserver: str,
    start_dir: str | None = None,
) -> dict[str, Any]:
    """Get configuration for a review sub-server.

    Parameters
    ----------
    subserver:
        Name of the sub-server (e.g., "scope", "quality", "security").
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    dict
        Configuration values for the sub-server.

    Examples
    --------
    >>> quality_config = get_review_config("quality")
    >>> isinstance(quality_config, dict)
    True
    """
    return get_section(f"review.{subserver}", start_dir=start_dir)


def get_fix_config(
    subserver: str,
    start_dir: str | None = None,
) -> dict[str, Any]:
    """Get configuration for a fix sub-server.

    Parameters
    ----------
    subserver:
        Name of the sub-server (e.g., "scope", "test", "lint").
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    dict
        Configuration values for the sub-server.

    Examples
    --------
    >>> test_config = get_fix_config("test")
    >>> isinstance(test_config, dict)
    True
    """
    return get_section(f"fix.{subserver}", start_dir=start_dir)


def get_tool_config(
    tool: str,
    start_dir: str | None = None,
) -> dict[str, Any]:
    """Get configuration for a specific tool.

    Parameters
    ----------
    tool:
        Name of the tool (e.g., "bandit", "radon", "pylint").
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    dict
        Configuration values for the tool.

    Examples
    --------
    >>> bandit_config = get_tool_config("bandit")
    >>> isinstance(bandit_config, dict)
    True
    """
    return get_section(f"tools.{tool}", start_dir=start_dir)


def clear_cache() -> None:
    """Clear the cached configuration.

    Use this when you need to force a reload of configuration,
    for example after modifying config files during testing.
    """
    global _cached_config
    _cached_config = None


# Alias for backward compatibility
def get_subserver_config(
    subserver: str,
    start_dir: str | None = None,
) -> dict[str, Any]:
    """Get configuration for a sub-server (alias for get_review_config).

    Parameters
    ----------
    subserver:
        Name of the sub-server (e.g., "scope", "quality", "security").
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    dict
        Configuration values for the sub-server.
    """
    return get_review_config(subserver, start_dir=start_dir)


def get_timeout(
    key: str,
    default: int,
    start_dir: str | None = None,
) -> int:
    """Get a timeout value from configuration.

    Parameters
    ----------
    key:
        Timeout key name (e.g., "git_quick_op", "tool_analysis").
    default:
        Default timeout in seconds if not configured.
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    int
        Timeout value in seconds.

    Examples
    --------
    >>> timeout = get_timeout("git_status", 10)
    >>> timeout >= 1
    True
    """
    timeouts = get_section("general.timeouts", start_dir=start_dir)
    return int(timeouts.get(key, default))


def get_display_limit(
    key: str,
    default: int,
    start_dir: str | None = None,
) -> int | None:
    """Get a display limit from configuration.

    Parameters
    ----------
    key:
        Display limit key name (e.g., "max_sample_files", "max_critical_display").
    default:
        Default limit if not configured.
    start_dir:
        Directory to start searching for project config files.

    Returns
    -------
    int or None
        Display limit (number of items), or None if unlimited (0 in config).

    Examples
    --------
    >>> limit = get_display_limit("max_sample_files", 10)
    >>> limit is None or limit >= 0
    True

    Notes
    -----
    Returns None for unlimited display (config value = 0).
    This allows code to use `items[:limit]` where `items[:None]` means all items.
    """
    display = get_section("output.display", start_dir=start_dir)
    limit = int(display.get(key, default))
    return None if limit == 0 else limit


def get_general_config(start_dir: str | None = None) -> dict[str, Any]:
    """Get general configuration settings.

    Returns
    -------
    dict
        General configuration with log_level, verbose, max_workers.
    """
    return get_section("general", start_dir=start_dir)


def get_log_level(start_dir: str | None = None) -> int:
    """Get the configured log level.

    Returns
    -------
    int
        Log level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL).
    """
    import logging

    general = get_general_config(start_dir)
    level_str = general.get("log_level", "INFO")

    # Handle both string and int values
    if isinstance(level_str, int):
        return level_str

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.INFO)


def get_verbose(start_dir: str | None = None) -> bool:
    """Get the verbose output setting.

    Returns
    -------
    bool
        True if verbose output is enabled.
    """
    general = get_general_config(start_dir)
    return bool(general.get("verbose", False))


def get_max_workers(start_dir: str | None = None) -> int:
    """Get the maximum number of parallel workers.

    Returns
    -------
    int
        Maximum parallel workers (default: 4).
    """
    general = get_general_config(start_dir)
    return int(general.get("max_workers", 4))


def get_output_config(start_dir: str | None = None) -> dict[str, Any]:
    """Get output configuration settings.

    Returns
    -------
    dict
        Output configuration with format, color, show_progress, etc.
    """
    return get_section("output", start_dir=start_dir)


def get_json_indent(start_dir: str | None = None) -> int:
    """Get JSON indentation level.

    Returns
    -------
    int
        JSON indent spaces (default: 2).
    """
    output = get_output_config(start_dir)
    return int(output.get("json_indent", 2))


def get_chunk_size(start_dir: str | None = None) -> int:
    """Get chunk size for splitting large issue files.

    Returns
    -------
    int
        Chunk size (default: 50).
    """
    output = get_output_config(start_dir)
    return int(output.get("chunk_size", 50))


def get_git_config(start_dir: str | None = None) -> dict[str, Any]:
    """Get git configuration settings.

    Returns
    -------
    dict
        Git configuration with commit_prefix, auto_commit, sign_commits, etc.
    """
    return get_section("git", start_dir=start_dir)


def get_commit_prefix(start_dir: str | None = None) -> str:
    """Get commit message prefix for automated commits.

    Returns
    -------
    str
        Commit prefix (default: "[glintefy]").
    """
    git = get_git_config(start_dir)
    return str(git.get("commit_prefix", "[glintefy]"))


def get_auto_commit(start_dir: str | None = None) -> bool:
    """Get auto-commit setting.

    Returns
    -------
    bool
        True if auto-commit is enabled (default: False).
    """
    git = get_git_config(start_dir)
    return bool(git.get("auto_commit", False))


def get_sign_commits(start_dir: str | None = None) -> bool:
    """Get GPG signing setting for commits.

    Returns
    -------
    bool
        True if commits should be signed (default: False).
    """
    git = get_git_config(start_dir)
    return bool(git.get("sign_commits", False))


def get_create_branch(start_dir: str | None = None) -> bool:
    """Get create branch setting for fixes.

    Returns
    -------
    bool
        True if a new branch should be created (default: False).
    """
    git = get_git_config(start_dir)
    return bool(git.get("create_branch", False))


def get_branch_template(start_dir: str | None = None) -> str:
    """Get branch name template for fix branches.

    Returns
    -------
    str
        Branch template (default: "fix/{issue_id}").
    """
    git = get_git_config(start_dir)
    return str(git.get("branch_template", "fix/{issue_id}"))
