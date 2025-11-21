"""Configuration loading using lib_layered_config.

Purpose
-------
Provide a centralized configuration loader that reads settings from:
1. Package defaults (defaultconfig.toml)
2. User config (~/.config/btx_fix_mcp/config.toml on Linux)
3. Project config (.btx-review.yaml or .btx-fix.yaml)
4. Environment variables (BTX_FIX_MCP_*)

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

from functools import lru_cache
from pathlib import Path
from typing import Any

from lib_layered_config import Config, read_config

from btx_fix_mcp.__init__conf__ import (
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
