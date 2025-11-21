"""Isolated virtual environment manager for analysis tools.

This module manages a separate venv for analysis tools (ruff, mypy, pylint, etc.)
that are used by the quality and security sub-servers. The venv is created
on-demand and tools are installed using uv for speed.

The venv is stored in ~/.cache/btx-fix-mcp/tools-venv/ and is shared across
all projects being analyzed.

Usage:
    from btx_fix_mcp.tools_venv import get_tool_path, ensure_tools_venv

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
from pathlib import Path
from typing import Optional

# Module-level state
_venv_initialized = False
_venv_path: Path | None = None

# Python version for the tools venv (matches requires-python in pyproject.toml)
PYTHON_VERSION = "3.13"

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


def get_cache_dir() -> Path:
    """Get the cache directory for btx-fix-mcp.

    Uses XDG_CACHE_HOME if set, otherwise ~/.cache/btx-fix-mcp/
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        base = Path(xdg_cache)
    else:
        base = Path.home() / ".cache"
    return base / "btx-fix-mcp"


def get_venv_path() -> Path:
    """Get the path to the tools virtual environment."""
    return get_cache_dir() / "tools-venv"


def get_tool_path(tool_name: str) -> Path:
    """Get the full path to a tool executable in the tools venv.

    Args:
        tool_name: Name of the tool (e.g., "ruff", "mypy", "pylint")

    Returns:
        Path to the tool executable

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
    marker = venv_path / ".btx-tools-version"
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

    Tries to find Python 3.13+, falls back to current interpreter.
    """
    # Try specific version first
    for version in ["3.13", "3.14", "3.12"]:
        python_name = f"python{version}"
        python_path = shutil.which(python_name)
        if python_path:
            return python_path

    # Fall back to generic python3
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

    This function is idempotent and fast if the venv already exists.
    It should be called by the orchestrator agent at startup, and by
    sub-agents if they're run independently.

    Args:
        force_update: If True, reinstall all tools even if venv exists

    Returns:
        Path to the venv directory

    Raises:
        RuntimeError: If venv creation or tool installation fails
    """
    global _venv_initialized, _venv_path

    # Fast path: already initialized in this process
    if _venv_initialized and not force_update:
        return get_venv_path()

    venv_path = get_venv_path()

    # Check if already initialized on disk
    if is_venv_initialized() and not force_update:
        _venv_initialized = True
        _venv_path = venv_path
        return venv_path

    # Create cache directory
    venv_path.parent.mkdir(parents=True, exist_ok=True)

    # Find Python interpreter
    python = _find_python()

    # Create venv if it doesn't exist
    if not venv_path.exists():
        subprocess.run(
            [python, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

    # Install uv first (for faster subsequent installs)
    uv = _install_uv_if_needed()

    # Get tools list
    tools = _get_tools_from_pyproject()

    # Install tools using uv
    venv_python = venv_path / "bin" / "python" if sys.platform != "win32" else venv_path / "Scripts" / "python.exe"

    subprocess.run(
        [str(uv), "pip", "install", "--python", str(venv_python), "--quiet"] + tools,
        check=True,
        capture_output=True,
    )

    # Write version marker
    marker = venv_path / ".btx-tools-version"
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
            # Most tools output "toolname X.Y.Z" or just "X.Y.Z"
            output = result.stdout.strip()
            # Try to extract version number
            parts = output.split()
            for part in parts:
                if part[0].isdigit():
                    return part
            return output
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
