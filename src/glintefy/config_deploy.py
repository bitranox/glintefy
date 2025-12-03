"""Configuration deployment functionality for CLI config-deploy command.

Purpose
-------
Provides the business logic for deploying default configuration to application,
host, or user configuration locations. Uses lib_layered_config's deploy_config
function to copy the bundled defaultconfig.toml to requested target layers.

Contents
--------
* :func:`deploy_configuration` - deploys configuration to specified targets

System Role
-----------
Lives in the behaviors layer. The CLI command delegates to this module for
all configuration deployment logic, keeping the CLI layer focused on argument
parsing and user interaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from lib_layered_config import deploy_config

from . import __init__conf__
from .config import _DEFAULT_CONFIG_FILE


def deploy_configuration(
    *,
    targets: Sequence[str],
    force: bool = False,
) -> list[Path]:
    """Deploy default configuration to specified target layers.

    Why
        Users need to initialize configuration files in standard locations
        (application, host, or user config directories) without manually
        copying files or knowing platform-specific paths.

    What
        Uses lib_layered_config.deploy_config() to copy the bundled
        defaultconfig.toml to requested target layers (app, host, user).
        Returns the list of created configuration file paths.

    Parameters
    ----------
    targets:
        Sequence of target layers to deploy to. Valid values: "app", "host", "user".
        Multiple targets can be specified to deploy to several locations at once.
    force:
        If True, overwrite existing configuration files. If False (default),
        skip files that already exist.

    Returns
    -------
    list[Path]:
        List of paths where configuration files were created or would be created.
        Empty list if all target files already exist and force=False.

    Side Effects
        Creates configuration files in platform-specific directories:
        - app: System-wide application config (requires privileges)
        - host: System-wide host config (requires privileges)
        - user: User-specific config (current user's home directory)

    Raises
    ------
    PermissionError:
        When deploying to app/host without sufficient privileges.
    ValueError:
        When invalid target names are provided.

    Notes
    -----
    Platform-specific paths:
    - Linux (app): /etc/xdg/{slug}/config.toml
    - Linux (host): /etc/xdg/{slug}/config.toml
    - Linux (user): ~/.config/{slug}/config.toml
    - macOS (app): /Library/Application Support/{vendor}/{app}/config.toml
    - macOS (user): ~/Library/Application Support/{vendor}/{app}/config.toml
    - Windows (app): C:\\ProgramData\\{vendor}\\{app}\\config.toml
    - Windows (user): %APPDATA%\\{vendor}\\{app}\\config.toml

    Examples
    --------
    >>> paths = deploy_configuration(targets=["user"])  # doctest: +SKIP
    >>> len(paths) > 0  # doctest: +SKIP
    True
    >>> paths[0].exists()  # doctest: +SKIP
    True
    """
    deployed_paths = deploy_config(
        source=_DEFAULT_CONFIG_FILE,
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        targets=targets,
        force=force,
    )

    return deployed_paths


__all__ = [
    "deploy_configuration",
]
