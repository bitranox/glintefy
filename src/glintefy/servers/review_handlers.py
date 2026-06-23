"""Tool call handlers for Review MCP Server.

Extracted from ReviewMCPServer to reduce class size, fix deep nesting,
and improve maintainability using a dispatch pattern.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from glintefy.subservers.common.logging import get_mcp_logger, log_debug, log_error_detailed

if TYPE_CHECKING:
    from glintefy.servers.review import ReviewMCPServer

logger = get_mcp_logger("glintefy.servers.review")


# Type alias for handler functions
ToolHandler = Callable[["ReviewMCPServer", dict[str, Any]], dict[str, Any]]


def _handle_scope(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_scope tool call."""
    return server.run_scope(mode=arguments.get("mode", "git"))


def _handle_quality(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_quality tool call."""
    return server.run_quality(
        complexity_threshold=arguments.get("complexity_threshold"),
        maintainability_threshold=arguments.get("maintainability_threshold"),
    )


def _handle_security(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_security tool call."""
    return server.run_security(
        severity_threshold=arguments.get("severity_threshold", "low"),
        confidence_threshold=arguments.get("confidence_threshold", "low"),
        critical_threshold=arguments.get("critical_threshold"),
        warning_threshold=arguments.get("warning_threshold"),
    )


def _handle_deps(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_deps tool call."""
    return server.run_deps(
        scan_vulnerabilities=arguments.get("scan_vulnerabilities", True),
        check_licenses=arguments.get("check_licenses", True),
        check_outdated=arguments.get("check_outdated", True),
    )


def _handle_docs(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_docs tool call."""
    return server.run_docs(
        min_coverage=arguments.get("min_coverage"),
        docstring_style=arguments.get("docstring_style"),
    )


def _handle_perf(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_perf tool call."""
    return server.run_perf(
        run_profiling=arguments.get("run_profiling", True),
        nested_loop_threshold=arguments.get("nested_loop_threshold"),
    )


def _handle_cache(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_cache tool call."""
    return server.run_cache(
        cache_size=arguments.get("cache_size", 128),
        hit_rate_threshold=arguments.get("hit_rate_threshold", 20.0),
        speedup_threshold=arguments.get("speedup_threshold", 5.0),
    )


def _handle_report(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_report tool call."""
    return server.run_report()


def _handle_all(server: "ReviewMCPServer", arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle review_all tool call."""
    return server.run_all(
        mode=arguments.get("mode", "git"),
        complexity_threshold=arguments.get("complexity_threshold"),
        severity_threshold=arguments.get("severity_threshold", "low"),
    )


# Dispatch table mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "review_scope": _handle_scope,
    "review_quality": _handle_quality,
    "review_security": _handle_security,
    "review_deps": _handle_deps,
    "review_docs": _handle_docs,
    "review_perf": _handle_perf,
    "review_cache": _handle_cache,
    "review_report": _handle_report,
    "review_all": _handle_all,
}


def handle_tool_call(
    server: "ReviewMCPServer",
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle an MCP tool call using dispatch pattern.

    This replaces the deeply nested if-elif chain with a simple lookup,
    reducing nesting depth from 9 to 2.

    Args:
        server: The ReviewMCPServer instance
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool execution result
    """
    log_debug(logger, f"Tool call: {name}", arguments=arguments)

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"status": "ERROR", "error": f"Unknown tool: {name}"}

    try:
        return handler(server, arguments)
    except Exception as e:
        log_error_detailed(logger, e, context={"tool": name, "arguments": arguments})
        return {"status": "ERROR", "error": str(e)}
