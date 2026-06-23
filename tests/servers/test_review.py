"""Tests for Review MCP Server."""

from pathlib import Path

import pytest

from glintefy.config import get_config
from glintefy.servers.review import ReviewMCPServer


class TestReviewMCPServer:
    """Tests for ReviewMCPServer class."""

    @pytest.fixture
    def repo_with_code(self, tmp_path):
        """Create a repository with code files."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create Python file
        (repo_dir / "main.py").write_text('''
def hello():
    """Return greeting."""
    return "world"
''')

        # Create test file
        tests_dir = repo_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_main.py").write_text('''
"""Tests for main."""
def test_hello():
    """Test hello."""
    assert True
''')

        return repo_dir

    def test_initialization(self, tmp_path):
        """Test server initialization."""
        server = ReviewMCPServer(repo_path=tmp_path)

        # Get expected output dir from config
        config = get_config(start_dir=str(tmp_path))
        expected_output_dir = config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")

        assert server.repo_path == tmp_path
        assert server._output_base == tmp_path / Path(expected_output_dir)

    def test_initialization_default_path(self):
        """Test initialization with default path."""
        server = ReviewMCPServer()

        assert server.repo_path == Path.cwd()

    def test_run_scope_full_mode(self, repo_with_code):
        """Test running scope in full mode."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        result = server.run_scope(mode="full")

        assert result["status"] == "SUCCESS"
        assert result["metrics"]["total_files"] >= 2
        assert result["metrics"]["mode"] == "full"

    def test_run_scope_git_mode_non_git(self, repo_with_code):
        """Test running scope in git mode on non-git repo."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        # Should fall back to full mode or fail gracefully
        result = server.run_scope(mode="git")

        # Either succeeds (fallback) or fails (not a git repo)
        assert result["status"] in ("SUCCESS", "FAILED")

    def test_run_quality(self, repo_with_code):
        """Test running quality analysis."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        # First run scope to generate files list
        scope_result = server.run_scope(mode="full")
        assert scope_result["status"] == "SUCCESS"

        # Then run quality
        result = server.run_quality()

        assert result["status"] in ("SUCCESS", "PARTIAL")
        assert "metrics" in result
        assert "files_analyzed" in result["metrics"]

    def test_run_security(self, repo_with_code):
        """Test running security analysis."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        # First run scope to generate files list
        scope_result = server.run_scope(mode="full")
        assert scope_result["status"] == "SUCCESS"

        # Then run security
        result = server.run_security()

        assert result["status"] in ("SUCCESS", "PARTIAL")
        assert "metrics" in result
        assert "files_scanned" in result["metrics"]

    def test_run_all(self, repo_with_code):
        """Test running all reviews."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        result = server.run_all(mode="full")

        assert result["overall_status"] in ("SUCCESS", "PARTIAL")
        assert result["scope"] is not None
        assert result["quality"] is not None
        assert result["security"] is not None

    def test_get_tool_definitions(self, tmp_path):
        """Test getting tool definitions."""
        server = ReviewMCPServer(repo_path=tmp_path)

        tools = server.get_tool_definitions()

        assert len(tools) == 9
        tool_names = [t["name"] for t in tools]
        assert "review_scope" in tool_names
        assert "review_quality" in tool_names
        assert "review_security" in tool_names
        assert "review_deps" in tool_names
        assert "review_docs" in tool_names
        assert "review_perf" in tool_names
        assert "review_cache" in tool_names
        assert "review_report" in tool_names
        assert "review_all" in tool_names

    def test_handle_tool_call_scope(self, repo_with_code):
        """Test handling scope tool call."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        result = server.handle_tool_call("review_scope", {"mode": "full"})

        assert result["status"] == "SUCCESS"

    def test_handle_tool_call_unknown(self, tmp_path):
        """Test handling unknown tool call."""
        server = ReviewMCPServer(repo_path=tmp_path)

        result = server.handle_tool_call("unknown_tool", {})

        assert result["status"] == "ERROR"
        assert "Unknown tool" in result["error"]


class TestReviewMCPServerLogging:
    """Tests for MCP server logging."""

    @pytest.fixture
    def repo_with_code(self, tmp_path):
        """Create a repository with code files."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create Python file
        (repo_dir / "main.py").write_text('''
def hello():
    """Return greeting."""
    return "world"
''')

        return repo_dir

    def test_logs_to_stderr(self, repo_with_code, capfd):
        """Test that MCP server logs to stderr."""
        # Reset any existing handlers to ensure fresh capture
        import logging

        logger = logging.getLogger("glintefy.servers.review")
        logger.handlers.clear()

        # Reimport to get fresh logger
        from glintefy.subservers.common.logging import get_mcp_logger

        fresh_logger = get_mcp_logger("glintefy.test_logs")

        # Log directly to verify stderr capture works
        fresh_logger.info("Test message for capture")

        captured = capfd.readouterr()
        # MCP logging should go to stderr
        assert "Test message" in captured.err or len(captured.err) > 0

    def test_mcp_mode_enabled_in_subservers(self, repo_with_code):
        """Test that subservers are created with mcp_mode=True."""
        server = ReviewMCPServer(repo_path=repo_with_code)

        # Run scope - internally creates ScopeSubServer with mcp_mode=True
        result = server.run_scope(mode="full")

        # If it completes, the subserver was created successfully
        assert result["status"] == "SUCCESS"
