"""Tests for review_handlers module."""

from unittest.mock import MagicMock

import pytest

from glintefy.servers.review_handlers import (
    TOOL_HANDLERS,
    _handle_all,
    _handle_cache,
    _handle_deps,
    _handle_docs,
    _handle_perf,
    _handle_quality,
    _handle_report,
    _handle_scope,
    _handle_security,
    handle_tool_call,
)


@pytest.fixture
def mock_server():
    """Create a mock ReviewMCPServer."""
    server = MagicMock()
    server.run_scope.return_value = {"status": "SUCCESS"}
    server.run_quality.return_value = {"status": "SUCCESS"}
    server.run_security.return_value = {"status": "SUCCESS"}
    server.run_deps.return_value = {"status": "SUCCESS"}
    server.run_docs.return_value = {"status": "SUCCESS"}
    server.run_perf.return_value = {"status": "SUCCESS"}
    server.run_cache.return_value = {"status": "SUCCESS"}
    server.run_report.return_value = {"status": "SUCCESS"}
    server.run_all.return_value = {"status": "SUCCESS"}
    return server


class TestHandleFunctions:
    """Tests for individual handler functions."""

    def test_handle_scope_default(self, mock_server):
        """Test _handle_scope with default mode."""
        _handle_scope(mock_server, {})
        mock_server.run_scope.assert_called_once_with(mode="git")

    def test_handle_scope_custom_mode(self, mock_server):
        """Test _handle_scope with full mode."""
        _handle_scope(mock_server, {"mode": "full"})
        mock_server.run_scope.assert_called_once_with(mode="full")

    def test_handle_quality_default(self, mock_server):
        """Test _handle_quality with default arguments."""
        _handle_quality(mock_server, {})
        mock_server.run_quality.assert_called_once_with(
            complexity_threshold=None,
            maintainability_threshold=None,
        )

    def test_handle_quality_custom(self, mock_server):
        """Test _handle_quality with custom thresholds."""
        _handle_quality(
            mock_server,
            {
                "complexity_threshold": 15,
                "maintainability_threshold": 25,
            },
        )
        mock_server.run_quality.assert_called_once_with(
            complexity_threshold=15,
            maintainability_threshold=25,
        )

    def test_handle_security_default(self, mock_server):
        """Test _handle_security with default arguments."""
        _handle_security(mock_server, {})
        mock_server.run_security.assert_called_once_with(
            severity_threshold="low",
            confidence_threshold="low",
            critical_threshold=None,
            warning_threshold=None,
        )

    def test_handle_security_custom(self, mock_server):
        """Test _handle_security with custom thresholds."""
        _handle_security(
            mock_server,
            {
                "severity_threshold": "high",
                "confidence_threshold": "medium",
                "critical_threshold": 3,
                "warning_threshold": 10,
            },
        )
        mock_server.run_security.assert_called_once_with(
            severity_threshold="high",
            confidence_threshold="medium",
            critical_threshold=3,
            warning_threshold=10,
        )

    def test_handle_deps_default(self, mock_server):
        """Test _handle_deps with default arguments."""
        _handle_deps(mock_server, {})
        mock_server.run_deps.assert_called_once_with(
            scan_vulnerabilities=True,
            check_licenses=True,
            check_outdated=True,
        )

    def test_handle_deps_custom(self, mock_server):
        """Test _handle_deps with custom flags."""
        _handle_deps(
            mock_server,
            {
                "scan_vulnerabilities": False,
                "check_licenses": False,
                "check_outdated": False,
            },
        )
        mock_server.run_deps.assert_called_once_with(
            scan_vulnerabilities=False,
            check_licenses=False,
            check_outdated=False,
        )

    def test_handle_docs_default(self, mock_server):
        """Test _handle_docs with default arguments."""
        _handle_docs(mock_server, {})
        mock_server.run_docs.assert_called_once_with(
            min_coverage=None,
            docstring_style=None,
        )

    def test_handle_docs_custom(self, mock_server):
        """Test _handle_docs with custom coverage and style."""
        _handle_docs(
            mock_server,
            {
                "min_coverage": 90,
                "docstring_style": "numpy",
            },
        )
        mock_server.run_docs.assert_called_once_with(
            min_coverage=90,
            docstring_style="numpy",
        )

    def test_handle_perf_default(self, mock_server):
        """Test _handle_perf with default arguments."""
        _handle_perf(mock_server, {})
        mock_server.run_perf.assert_called_once_with(
            run_profiling=True,
            nested_loop_threshold=None,
        )

    def test_handle_perf_custom(self, mock_server):
        """Test _handle_perf with custom profiling and threshold."""
        _handle_perf(
            mock_server,
            {
                "run_profiling": False,
                "nested_loop_threshold": 3,
            },
        )
        mock_server.run_perf.assert_called_once_with(
            run_profiling=False,
            nested_loop_threshold=3,
        )

    def test_handle_cache_default(self, mock_server):
        """Test _handle_cache with default arguments."""
        _handle_cache(mock_server, {})
        mock_server.run_cache.assert_called_once_with(
            cache_size=128,
            hit_rate_threshold=20.0,
            speedup_threshold=5.0,
        )

    def test_handle_cache_custom(self, mock_server):
        """Test _handle_cache with custom parameters."""
        _handle_cache(
            mock_server,
            {
                "cache_size": 256,
                "hit_rate_threshold": 30.0,
                "speedup_threshold": 10.0,
            },
        )
        mock_server.run_cache.assert_called_once_with(
            cache_size=256,
            hit_rate_threshold=30.0,
            speedup_threshold=10.0,
        )

    def test_handle_report(self, mock_server):
        """Test _handle_report."""
        _handle_report(mock_server, {})
        mock_server.run_report.assert_called_once()

    def test_handle_all_default(self, mock_server):
        """Test _handle_all with default arguments."""
        _handle_all(mock_server, {})
        mock_server.run_all.assert_called_once_with(
            mode="git",
            complexity_threshold=None,
            severity_threshold="low",
        )

    def test_handle_all_custom(self, mock_server):
        """Test _handle_all with custom arguments."""
        _handle_all(
            mock_server,
            {
                "mode": "full",
                "complexity_threshold": 10,
                "severity_threshold": "high",
            },
        )
        mock_server.run_all.assert_called_once_with(
            mode="full",
            complexity_threshold=10,
            severity_threshold="high",
        )


class TestToolHandlersDict:
    """Tests for TOOL_HANDLERS dictionary."""

    def test_all_tools_registered(self):
        """Test all expected tools are in TOOL_HANDLERS."""
        expected_tools = [
            "review_scope",
            "review_quality",
            "review_security",
            "review_deps",
            "review_docs",
            "review_perf",
            "review_report",
            "review_all",
        ]
        for tool in expected_tools:
            assert tool in TOOL_HANDLERS

    def test_handlers_are_callable(self):
        """Test all handlers are callable."""
        for name, handler in TOOL_HANDLERS.items():
            assert callable(handler), f"Handler for {name} is not callable"


class TestHandleToolCall:
    """Tests for handle_tool_call function."""

    def test_handle_tool_call_success(self, mock_server):
        """Test successful tool call handling."""
        result = handle_tool_call(mock_server, "review_scope", {"mode": "git"})
        assert result == {"status": "SUCCESS"}

    def test_handle_tool_call_unknown_tool(self, mock_server):
        """Test handling of unknown tool."""
        result = handle_tool_call(mock_server, "unknown_tool", {})
        assert result["status"] == "ERROR"
        assert "Unknown tool" in result["error"]

    def test_handle_tool_call_exception(self, mock_server):
        """Test handling of exception during tool execution."""
        mock_server.run_scope.side_effect = RuntimeError("Test error")

        result = handle_tool_call(mock_server, "review_scope", {})

        assert result["status"] == "ERROR"
        assert "Test error" in result["error"]

    def test_handle_tool_call_all_tools(self, mock_server):
        """Test calling all tools via handle_tool_call."""
        for tool_name in TOOL_HANDLERS:
            result = handle_tool_call(mock_server, tool_name, {})
            assert "status" in result
