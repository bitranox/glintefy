"""Isolated virtual environment manager for analysis tools.

This module manages a separate venv for analysis tools (ruff, mypy, pylint, etc.)
that are used by the quality and security sub-servers. The venv is created
on-demand and tools are installed using uv for speed.

The venv is stored in ~/.cache/glintefy/tools-venv/ and is shared across
all projects being analyzed.

Usage:
    from glintefy.tools_venv import get_tool_path, ensure_tools_venv

    # Ensure venv exists and tools are installed (idempotent, fast if already done)
    ensure_tools_venv()

    # Get path to a tool executable
    ruff_path = get_tool_path("ruff")

    # Use in subprocess
    subprocess.run([ruff_path, "check", "src/"])
"""

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# Module-level state
_venv_initialized = False
_venv_path: Path | None = None

# Minimum supported Python version
MIN_PYTHON_VERSION = (3, 13)

# Tools to install in the venv (read from pyproject.toml at runtime)
DEFAULT_TOOLS = [
    "ruff>=0.14.0",
    "mypy>=1.8.0",
    "pylint>=3.0.0",
    "vulture>=2.11",
    "interrogate>=1.5.0",
    "beartype>=0.18.0",
    "radon>=6.0.0",
    "bandit>=1.7.0",
]


@lru_cache(maxsize=1)
def get_cache_dir() -> Path:
    """Get the cache directory for glintefy (cached).

    Uses XDG_CACHE_HOME if set, otherwise ~/.cache/glintefy/

    Returns are cached for performance.
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        base = Path(xdg_cache)
    else:
        base = Path.home() / ".cache"
    return base / "glintefy"


@lru_cache(maxsize=1)
def get_venv_path() -> Path:
    """Get the path to the tools virtual environment (cached)."""
    return get_cache_dir() / "tools-venv"


@lru_cache(maxsize=32)
def get_tool_path(tool_name: str) -> Path:
    """Get the full path to a tool executable in the tools venv (cached).

    Args:
        tool_name: Name of the tool (e.g., "ruff", "mypy", "pylint")

    Returns:
        Path to the tool executable

    Note:
        Results are cached for performance as tool paths don't change.

    Example:
        >>> ruff = get_tool_path("ruff")
        >>> subprocess.run([str(ruff), "check", "src/"])
    """
    venv_path = get_venv_path()
    if sys.platform == "win32":
        return venv_path / "Scripts" / f"{tool_name}.exe"
    return venv_path / "bin" / tool_name


def is_venv_initialized() -> bool:
    """Check if the tools venv is initialized and has required tools."""
    venv_path = get_venv_path()
    if not venv_path.exists():
        return False

    # Check for a few key tools to verify installation
    for tool in ["ruff", "mypy", "pylint"]:
        tool_path = get_tool_path(tool)
        if not tool_path.exists():
            return False

    # Check marker file for version
    marker = venv_path / ".glintefy-tools-version"
    if not marker.exists():
        return False

    return True


def _get_tools_from_pyproject() -> list[str]:
    """Read tools list from pyproject.toml if available."""
    try:
        # Try to find pyproject.toml relative to this module
        module_dir = Path(__file__).parent
        pyproject_path = module_dir.parent.parent.parent / "pyproject.toml"

        if not pyproject_path.exists():
            return DEFAULT_TOOLS

        # Use tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        tools = data.get("project", {}).get("optional-dependencies", {}).get("tools", [])
        return tools if tools else DEFAULT_TOOLS

    except Exception:
        return DEFAULT_TOOLS


def _find_python() -> str:
    """Find a suitable Python interpreter for the venv.

    Tries to find the latest Python (3.20 down to 3.13), falls back to current interpreter.
    Minimum supported version is 3.13.
    """
    # Try versions in descending order (newest first)
    # Range: 3.20 down to 3.13 (covers future versions)
    for minor in range(20, MIN_PYTHON_VERSION[1] - 1, -1):
        python_name = f"python3.{minor}"
        python_path = shutil.which(python_name)
        if python_path:
            return python_path

    # Fall back to generic python3 (may be 3.13+)
    python3 = shutil.which("python3")
    if python3:
        return python3

    # Last resort: current interpreter
    return sys.executable


def _install_uv_if_needed() -> Path:
    """Ensure uv is available, install if needed.

    Returns:
        Path to the uv executable
    """
    # Check if uv is already installed system-wide
    uv_path = shutil.which("uv")
    if uv_path:
        return Path(uv_path)

    # Check if uv is in the tools venv
    venv_uv = get_tool_path("uv")
    if venv_uv.exists():
        return venv_uv

    # Install uv using pip in the tools venv (bootstrap)
    venv_path = get_venv_path()
    venv_pip = venv_path / "bin" / "pip" if sys.platform != "win32" else venv_path / "Scripts" / "pip.exe"

    if venv_pip.exists():
        subprocess.run(
            [str(venv_pip), "install", "--quiet", "uv"],
            check=True,
            capture_output=True,
        )
        return venv_uv

    # If venv doesn't exist yet, install uv system-wide temporarily
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--user", "uv"],
        check=True,
        capture_output=True,
    )
    uv_path = shutil.which("uv")
    if uv_path:
        return Path(uv_path)

    raise RuntimeError("Failed to install uv package manager")


def ensure_tools_venv(force_update: bool = False) -> Path:
    """Ensure the tools virtual environment exists and has required tools.

    Creates the venv if needed and always upgrades tools to latest versions.
    The upgrade is fast (uv checks versions quickly) and ensures tools stay current.

    Args:
        force_update: If True, recreate venv from scratch

    Returns:
        Path to the venv directory

    Raises:
        RuntimeError: If venv creation or tool installation fails
    """
    global _venv_initialized, _venv_path

    # Fast path: already initialized AND upgraded in this process
    if _venv_initialized and not force_update:
        return get_venv_path()

    venv_path = get_venv_path()

    # Create cache directory
    venv_path.parent.mkdir(parents=True, exist_ok=True)

    # Find Python interpreter
    python = _find_python()

    # Create venv if it doesn't exist (or force recreate)
    if not venv_path.exists() or force_update:
        if venv_path.exists():
            shutil.rmtree(venv_path)
        subprocess.run(
            [python, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

    # Install uv first (for faster subsequent installs)
    uv = _install_uv_if_needed()

    # Get tools list
    tools = _get_tools_from_pyproject()

    # Install/upgrade tools using uv
    # Always upgrade to latest versions matching the version specs
    # uv is fast - it checks versions and only downloads if needed
    venv_python = venv_path / "bin" / "python" if sys.platform != "win32" else venv_path / "Scripts" / "python.exe"

    subprocess.run(
        [str(uv), "pip", "install", "--upgrade", "--python", str(venv_python), "--quiet"] + tools,
        check=True,
        capture_output=True,
    )

    # Write version marker
    marker = venv_path / ".glintefy-tools-version"
    marker.write_text("1.0")

    _venv_initialized = True
    _venv_path = venv_path

    return venv_path


def run_tool(tool_name: str, args: list[str], **subprocess_kwargs) -> subprocess.CompletedProcess:
    """Run a tool from the tools venv.

    Ensures the venv is initialized before running.

    Args:
        tool_name: Name of the tool (e.g., "ruff", "mypy")
        args: Arguments to pass to the tool
        **subprocess_kwargs: Additional arguments for subprocess.run

    Returns:
        CompletedProcess from subprocess.run

    Example:
        >>> result = run_tool("ruff", ["check", "src/"], capture_output=True, text=True)
        >>> print(result.stdout)
    """
    ensure_tools_venv()
    tool_path = get_tool_path(tool_name)

    if not tool_path.exists():
        raise FileNotFoundError(f"Tool '{tool_name}' not found in tools venv at {tool_path}")

    return subprocess.run([str(tool_path)] + args, **subprocess_kwargs)


def _extract_version_from_output(output: str) -> str:
    """Extract version number from tool version output.

    Args:
        output: Version command output

    Returns:
        Version string (either extracted number or full output)
    """
    parts = output.split()
    for part in parts:
        if part and part[0].isdigit():
            return part
    return output


def get_tool_version(tool_name: str) -> str | None:
    """Get the version of a tool in the tools venv.

    Args:
        tool_name: Name of the tool

    Returns:
        Version string or None if tool not found/version check failed
    """
    try:
        result = run_tool(tool_name, ["--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout.strip()
            return _extract_version_from_output(output)
    except Exception:
        pass
    return None


def cleanup_tools_venv() -> None:
    """Remove the tools virtual environment.

    Use this if you need to force a fresh installation.
    """
    global _venv_initialized, _venv_path

    venv_path = get_venv_path()
    if venv_path.exists():
        shutil.rmtree(venv_path)

    _venv_initialized = False
    _venv_path = None
