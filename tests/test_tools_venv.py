"""Tests for tools_venv module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from btx_fix_mcp.tools_venv import (
    DEFAULT_TOOLS,
    _find_python,
    _get_tools_from_pyproject,
    get_cache_dir,
    get_tool_path,
    get_venv_path,
    is_venv_initialized,
)


class TestCacheDir:
    """Tests for cache directory functions."""

    def test_get_cache_dir_default(self):
        """Test default cache directory is under home."""
        with patch.dict("os.environ", {}, clear=True):
            cache_dir = get_cache_dir()
            assert cache_dir.name == "btx-fix-mcp"
            assert ".cache" in str(cache_dir)

    def test_get_cache_dir_xdg(self, tmp_path):
        """Test XDG_CACHE_HOME is respected."""
        with patch.dict("os.environ", {"XDG_CACHE_HOME": str(tmp_path)}):
            cache_dir = get_cache_dir()
            assert cache_dir == tmp_path / "btx-fix-mcp"

    def test_get_venv_path(self):
        """Test venv path is under cache dir."""
        venv_path = get_venv_path()
        assert venv_path.name == "tools-venv"
        assert "btx-fix-mcp" in str(venv_path)


class TestToolPath:
    """Tests for tool path functions."""

    def test_get_tool_path_linux(self):
        """Test tool path on Linux/macOS."""
        with patch.object(sys, "platform", "linux"):
            tool_path = get_tool_path("ruff")
            assert tool_path.name == "ruff"
            assert "bin" in str(tool_path)

    def test_get_tool_path_windows(self):
        """Test tool path on Windows."""
        with patch.object(sys, "platform", "win32"):
            tool_path = get_tool_path("ruff")
            assert tool_path.name == "ruff.exe"
            assert "Scripts" in str(tool_path)


class TestVenvInitialization:
    """Tests for venv initialization detection."""

    def test_is_venv_initialized_no_venv(self, tmp_path):
        """Test returns False when venv doesn't exist."""
        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=tmp_path / "nonexistent"):
            assert is_venv_initialized() is False

    def test_is_venv_initialized_empty_venv(self, tmp_path):
        """Test returns False when venv exists but is empty."""
        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=venv_path):
            assert is_venv_initialized() is False

    def test_is_venv_initialized_no_marker(self, tmp_path):
        """Test returns False when marker file is missing."""
        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        bin_dir = venv_path / "bin"
        bin_dir.mkdir()
        # Create tool files but no marker
        for tool in ["ruff", "mypy", "pylint"]:
            (bin_dir / tool).touch()

        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=venv_path):
            with patch.object(sys, "platform", "linux"):
                assert is_venv_initialized() is False

    def test_is_venv_initialized_complete(self, tmp_path):
        """Test returns True when venv is complete."""
        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        bin_dir = venv_path / "bin"
        bin_dir.mkdir()
        # Create tool files
        for tool in ["ruff", "mypy", "pylint"]:
            (bin_dir / tool).touch()
        # Create marker file
        (venv_path / ".btx-tools-version").write_text("1.0")

        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=venv_path):
            with patch.object(sys, "platform", "linux"):
                assert is_venv_initialized() is True


class TestToolsFromPyproject:
    """Tests for reading tools from pyproject.toml."""

    def test_get_tools_from_pyproject_fallback(self, tmp_path):
        """Test fallback to DEFAULT_TOOLS when pyproject.toml not found."""
        with patch("btx_fix_mcp.tools_venv.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.__truediv__.return_value.exists.return_value = False
            tools = _get_tools_from_pyproject()
            # Should return default tools
            assert tools == DEFAULT_TOOLS

    def test_default_tools_has_required_packages(self):
        """Test DEFAULT_TOOLS includes all required analysis tools."""
        tool_names = [t.split(">=")[0] for t in DEFAULT_TOOLS]
        required = ["ruff", "mypy", "pylint", "vulture", "interrogate", "beartype", "radon", "bandit"]
        for req in required:
            assert req in tool_names, f"Missing required tool: {req}"


class TestFindPython:
    """Tests for Python interpreter discovery."""

    def test_find_python_returns_executable(self):
        """Test _find_python returns a valid path."""
        python = _find_python()
        assert python is not None
        assert Path(python).exists() or python == sys.executable

    def test_find_python_fallback_to_current(self):
        """Test fallback to current interpreter when others not found."""
        with patch("shutil.which", return_value=None):
            python = _find_python()
            assert python == sys.executable


class TestEnsureToolsVenvMocked:
    """Tests for ensure_tools_venv with mocking (no actual venv creation)."""

    def test_ensure_tools_venv_fast_path(self, tmp_path):
        """Test fast path when already initialized."""
        import btx_fix_mcp.tools_venv as module

        # Set up mock state
        original_initialized = module._venv_initialized
        original_path = module._venv_path

        try:
            module._venv_initialized = True
            module._venv_path = tmp_path

            with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=tmp_path):
                result = module.ensure_tools_venv()
                assert result == tmp_path
        finally:
            module._venv_initialized = original_initialized
            module._venv_path = original_path

    def test_ensure_tools_venv_skip_if_disk_initialized(self, tmp_path):
        """Test skips creation when already on disk."""
        import btx_fix_mcp.tools_venv as module

        original_initialized = module._venv_initialized

        try:
            module._venv_initialized = False

            with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=tmp_path):
                with patch("btx_fix_mcp.tools_venv.is_venv_initialized", return_value=True):
                    result = module.ensure_tools_venv()
                    assert result == tmp_path
                    assert module._venv_initialized is True
        finally:
            module._venv_initialized = original_initialized


class TestRunTool:
    """Tests for run_tool function."""

    def test_run_tool_not_found(self, tmp_path):
        """Test FileNotFoundError when tool doesn't exist."""
        from btx_fix_mcp.tools_venv import run_tool

        with patch("btx_fix_mcp.tools_venv.ensure_tools_venv"):
            with patch("btx_fix_mcp.tools_venv.get_tool_path", return_value=tmp_path / "nonexistent"):
                with pytest.raises(FileNotFoundError, match="not found in tools venv"):
                    run_tool("nonexistent", ["--version"])


class TestCleanupToolsVenv:
    """Tests for cleanup function."""

    def test_cleanup_tools_venv(self, tmp_path):
        """Test cleanup removes venv directory."""
        from btx_fix_mcp.tools_venv import cleanup_tools_venv

        import btx_fix_mcp.tools_venv as module

        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        (venv_path / "somefile").touch()

        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=venv_path):
            cleanup_tools_venv()
            assert not venv_path.exists()
            assert module._venv_initialized is False

    def test_cleanup_nonexistent_venv(self, tmp_path):
        """Test cleanup handles nonexistent venv gracefully."""
        from btx_fix_mcp.tools_venv import cleanup_tools_venv

        with patch("btx_fix_mcp.tools_venv.get_venv_path", return_value=tmp_path / "nonexistent"):
            # Should not raise
            cleanup_tools_venv()
