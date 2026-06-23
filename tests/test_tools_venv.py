"""Tests for tools_venv module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glintefy.tools_venv import (
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

    def setup_method(self):
        """Clear caches before each test."""
        get_cache_dir.cache_clear()
        get_venv_path.cache_clear()
        get_tool_path.cache_clear()

    def test_get_cache_dir_default(self):
        """Test default cache directory is under home."""
        # Don't clear env completely - Windows needs USERPROFILE/HOMEDRIVE for Path.home()
        # Just remove XDG_CACHE_HOME to test default behavior
        env_without_xdg = {k: v for k, v in __import__("os").environ.items() if k != "XDG_CACHE_HOME"}
        with patch.dict("os.environ", env_without_xdg, clear=True):
            cache_dir = get_cache_dir()
            assert cache_dir.name == "glintefy"
            assert ".cache" in str(cache_dir)

    def test_get_cache_dir_xdg(self, tmp_path):
        """Test XDG_CACHE_HOME is respected."""
        with patch.dict("os.environ", {"XDG_CACHE_HOME": str(tmp_path)}):
            cache_dir = get_cache_dir()
            assert cache_dir == tmp_path / "glintefy"

    def test_get_venv_path(self):
        """Test venv path is under cache dir."""
        venv_path = get_venv_path()
        assert venv_path.name == "tools-venv"
        assert "glintefy" in str(venv_path)


class TestToolPath:
    """Tests for tool path functions."""

    def setup_method(self):
        """Clear caches before each test."""
        get_cache_dir.cache_clear()
        get_venv_path.cache_clear()
        get_tool_path.cache_clear()

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

    def setup_method(self):
        """Clear caches before each test."""
        get_cache_dir.cache_clear()
        get_venv_path.cache_clear()
        get_tool_path.cache_clear()

    def test_is_venv_initialized_no_venv(self, tmp_path):
        """Test returns False when venv doesn't exist."""
        with patch("glintefy.tools_venv.get_venv_path", return_value=tmp_path / "nonexistent"):
            assert is_venv_initialized() is False

    def test_is_venv_initialized_empty_venv(self, tmp_path):
        """Test returns False when venv exists but is empty."""
        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        with patch("glintefy.tools_venv.get_venv_path", return_value=venv_path):
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

        with patch("glintefy.tools_venv.get_venv_path", return_value=venv_path):
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
        (venv_path / ".glintefy-tools-version").write_text("1.0")

        with patch("glintefy.tools_venv.get_venv_path", return_value=venv_path):
            with patch.object(sys, "platform", "linux"):
                assert is_venv_initialized() is True


class TestToolsFromPyproject:
    """Tests for reading tools from pyproject.toml."""

    def test_get_tools_from_pyproject_fallback(self, tmp_path):
        """Test fallback to DEFAULT_TOOLS when pyproject.toml not found."""
        with patch("glintefy.tools_venv.Path") as mock_path:
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
        import glintefy.tools_venv as module

        # Set up mock state
        original_initialized = module._venv_initialized
        original_path = module._venv_path

        try:
            module._venv_initialized = True
            module._venv_path = tmp_path

            with patch("glintefy.tools_venv.get_venv_path", return_value=tmp_path):
                result = module.ensure_tools_venv()
                assert result == tmp_path
        finally:
            module._venv_initialized = original_initialized
            module._venv_path = original_path

    def test_ensure_tools_venv_upgrades_existing(self, tmp_path):
        """Test upgrades tools in existing venv."""
        import glintefy.tools_venv as module

        original_initialized = module._venv_initialized

        try:
            module._venv_initialized = False

            # Mock all subprocess calls and dependencies
            with patch("glintefy.tools_venv.get_venv_path", return_value=tmp_path):
                with patch("glintefy.tools_venv._find_python", return_value=sys.executable):
                    with patch("glintefy.tools_venv._install_uv_if_needed", return_value=Path("/usr/bin/uv")):
                        with patch("subprocess.run") as mock_run:
                            mock_run.return_value = MagicMock(returncode=0)
                            # Create marker to simulate existing venv
                            tmp_path.mkdir(exist_ok=True)

                            result = module.ensure_tools_venv()

                            assert result == tmp_path
                            assert module._venv_initialized is True
                            # Verify upgrade was called with --upgrade flag
                            install_calls = [c for c in mock_run.call_args_list if "--upgrade" in str(c)]
                            assert len(install_calls) > 0, "Should have called install with --upgrade"
        finally:
            module._venv_initialized = original_initialized


class TestRunTool:
    """Tests for run_tool function."""

    def test_run_tool_not_found(self, tmp_path):
        """Test FileNotFoundError when tool doesn't exist."""
        from glintefy.tools_venv import run_tool

        with patch("glintefy.tools_venv.ensure_tools_venv"):
            with patch("glintefy.tools_venv.get_tool_path", return_value=tmp_path / "nonexistent"):
                with pytest.raises(FileNotFoundError, match="not found in tools venv"):
                    run_tool("nonexistent", ["--version"])


class TestCleanupToolsVenv:
    """Tests for cleanup function."""

    def test_cleanup_tools_venv(self, tmp_path):
        """Test cleanup removes venv directory."""
        from glintefy.tools_venv import cleanup_tools_venv

        import glintefy.tools_venv as module

        venv_path = tmp_path / "tools-venv"
        venv_path.mkdir()
        (venv_path / "somefile").touch()

        with patch("glintefy.tools_venv.get_venv_path", return_value=venv_path):
            cleanup_tools_venv()
            assert not venv_path.exists()
            assert module._venv_initialized is False

    def test_cleanup_nonexistent_venv(self, tmp_path):
        """Test cleanup handles nonexistent venv gracefully."""
        from glintefy.tools_venv import cleanup_tools_venv

        with patch("glintefy.tools_venv.get_venv_path", return_value=tmp_path / "nonexistent"):
            # Should not raise
            cleanup_tools_venv()


class TestGetToolsFromPyprojectAdvanced:
    """Additional tests for pyproject.toml reading."""

    def test_get_tools_with_valid_pyproject(self, tmp_path):
        """Test reading tools from a valid pyproject.toml."""
        # The function uses Path(__file__) which we can't easily mock
        # Just test that the function returns a list
        tools = _get_tools_from_pyproject()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_tools_exception_handling(self):
        """Test exception handling returns DEFAULT_TOOLS."""
        with patch("glintefy.tools_venv.Path", side_effect=Exception("test error")):
            tools = _get_tools_from_pyproject()
            assert tools == DEFAULT_TOOLS


class TestInstallUvIfNeeded:
    """Tests for _install_uv_if_needed function."""

    def test_install_uv_system_found(self, tmp_path):
        """Test uv found in system PATH."""
        from glintefy.tools_venv import _install_uv_if_needed

        uv_path = tmp_path / "uv"
        uv_path.touch()

        with patch("shutil.which", return_value=str(uv_path)):
            result = _install_uv_if_needed()
            assert result == uv_path

    def test_install_uv_in_venv(self, tmp_path):
        """Test uv found in tools venv."""
        from glintefy.tools_venv import _install_uv_if_needed

        venv_path = tmp_path / "tools-venv"
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(parents=True)
        uv_path = bin_dir / "uv"
        uv_path.touch()

        with patch("shutil.which", return_value=None):
            with patch("glintefy.tools_venv.get_tool_path", return_value=uv_path):
                result = _install_uv_if_needed()
                assert result == uv_path

    def test_install_uv_via_pip_in_venv(self, tmp_path):
        """Test installing uv via pip in existing venv."""
        from glintefy.tools_venv import _install_uv_if_needed

        venv_path = tmp_path / "tools-venv"
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(parents=True)
        pip_path = bin_dir / "pip"
        pip_path.touch()
        uv_path = bin_dir / "uv"

        with patch("shutil.which", return_value=None):
            with patch("glintefy.tools_venv.get_venv_path", return_value=venv_path):
                with patch("glintefy.tools_venv.get_tool_path", return_value=uv_path):
                    with patch.object(sys, "platform", "linux"):
                        with patch("subprocess.run") as mock_run:
                            mock_run.return_value.returncode = 0
                            _install_uv_if_needed()
                            # Should call pip install uv
                            mock_run.assert_called_once()
                            assert "uv" in mock_run.call_args[0][0]


class TestRunToolSuccess:
    """Tests for run_tool success path."""

    def test_run_tool_success(self, tmp_path):
        """Test run_tool with existing tool."""
        from glintefy.tools_venv import run_tool
        import subprocess

        tool_path = tmp_path / "mytool"
        tool_path.touch()
        tool_path.chmod(0o755)

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="output", stderr="")

        with patch("glintefy.tools_venv.ensure_tools_venv"):
            with patch("glintefy.tools_venv.get_tool_path", return_value=tool_path):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = run_tool("mytool", ["--version"], capture_output=True)
                    assert result.returncode == 0
                    mock_run.assert_called_once()


class TestGetToolVersion:
    """Tests for get_tool_version function."""

    def test_get_tool_version_success(self):
        """Test getting tool version successfully."""
        from glintefy.tools_venv import get_tool_version
        import subprocess

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="ruff 0.14.0", stderr="")

        with patch("glintefy.tools_venv.run_tool", return_value=mock_result):
            version = get_tool_version("ruff")
            assert version == "0.14.0"

    def test_get_tool_version_just_number(self):
        """Test getting version when output is just the number."""
        from glintefy.tools_venv import get_tool_version
        import subprocess

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="1.2.3", stderr="")

        with patch("glintefy.tools_venv.run_tool", return_value=mock_result):
            version = get_tool_version("mytool")
            assert version == "1.2.3"

    def test_get_tool_version_failure(self):
        """Test version extraction when tool fails."""
        from glintefy.tools_venv import get_tool_version
        import subprocess

        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")

        with patch("glintefy.tools_venv.run_tool", return_value=mock_result):
            version = get_tool_version("mytool")
            assert version is None

    def test_get_tool_version_exception(self):
        """Test version extraction when exception occurs."""
        from glintefy.tools_venv import get_tool_version

        with patch("glintefy.tools_venv.run_tool", side_effect=Exception("error")):
            version = get_tool_version("mytool")
            assert version is None

    def test_get_tool_version_no_digit_start(self):
        """Test version extraction when no part starts with digit."""
        from glintefy.tools_venv import get_tool_version
        import subprocess

        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="version unknown", stderr="")

        with patch("glintefy.tools_venv.run_tool", return_value=mock_result):
            version = get_tool_version("mytool")
            assert version == "version unknown"


class TestFindPythonAdvanced:
    """Additional tests for Python discovery."""

    def test_find_python_specific_version(self):
        """Test finding specific Python version."""

        def which_side_effect(name):
            if name == "python3.13":
                return "/usr/bin/python3.13"
            return None

        with patch("shutil.which", side_effect=which_side_effect):
            python = _find_python()
            assert python == "/usr/bin/python3.13"

    def test_find_python_fallback_to_python3(self):
        """Test fallback to generic python3."""

        def which_side_effect(name):
            if name == "python3":
                return "/usr/bin/python3"
            return None

        with patch("shutil.which", side_effect=which_side_effect):
            python = _find_python()
            assert python == "/usr/bin/python3"
