"""Tool definitions for Review MCP Server.

Extracted from ReviewMCPServer to reduce class size and improve maintainability.
"""

from typing import Any

from btx_fix_mcp.subservers.common.mindsets import (
    DEPS_MINDSET,
    DOCS_MINDSET,
    PERF_MINDSET,
    QUALITY_MINDSET,
    SECURITY_MINDSET,
    get_mindset,
)


def get_review_tool_definitions() -> list[dict[str, Any]]:
    """Get MCP tool definitions for the review server.

    Tool descriptions include the reviewer mindset to guide the analysis.

    Returns:
        List of tool definition dictionaries for MCP protocol
    """
    quality_mindset = get_mindset(QUALITY_MINDSET)
    security_mindset = get_mindset(SECURITY_MINDSET)
    deps_mindset = get_mindset(DEPS_MINDSET)
    docs_mindset = get_mindset(DOCS_MINDSET)
    perf_mindset = get_mindset(PERF_MINDSET)

    return [
        _scope_tool_definition(),
        _quality_tool_definition(quality_mindset),
        _security_tool_definition(security_mindset),
        _deps_tool_definition(deps_mindset),
        _docs_tool_definition(docs_mindset),
        _perf_tool_definition(perf_mindset),
        _report_tool_definition(),
        _all_tool_definition(),
    ]


def _scope_tool_definition() -> dict[str, Any]:
    """Return scope tool definition."""
    return {
        "name": "review_scope",
        "description": "Determine which files need to be reviewed based on git changes or full scan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["git", "full"],
                    "description": "Scan mode: 'git' for uncommitted changes, 'full' for all files",
                    "default": "git",
                },
            },
        },
    }


def _quality_tool_definition(mindset: Any) -> dict[str, Any]:
    """Return quality tool definition."""
    return {
        "name": "review_quality",
        "description": f"""Analyze code quality including complexity, maintainability, and style issues.

{mindset.format_for_tool_description()}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "complexity_threshold": {
                    "type": "integer",
                    "description": "Maximum cyclomatic complexity before flagging (default: 10)",
                },
                "maintainability_threshold": {
                    "type": "integer",
                    "description": "Minimum maintainability index (default: 20)",
                },
            },
        },
    }


def _security_tool_definition(mindset: Any) -> dict[str, Any]:
    """Return security tool definition."""
    return {
        "name": "review_security",
        "description": f"""Scan code for security vulnerabilities using Bandit.

{mindset.format_for_tool_description()}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "severity_threshold": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Minimum severity to report",
                    "default": "low",
                },
                "confidence_threshold": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Minimum confidence to report",
                    "default": "low",
                },
            },
        },
    }


def _deps_tool_definition(mindset: Any) -> dict[str, Any]:
    """Return deps tool definition."""
    return {
        "name": "review_deps",
        "description": f"""Analyze project dependencies for vulnerabilities and compliance.

{mindset.format_for_tool_description()}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scan_vulnerabilities": {
                    "type": "boolean",
                    "description": "Enable vulnerability scanning (default: true)",
                    "default": True,
                },
                "check_licenses": {
                    "type": "boolean",
                    "description": "Enable license compliance checking (default: true)",
                    "default": True,
                },
                "check_outdated": {
                    "type": "boolean",
                    "description": "Enable outdated package detection (default: true)",
                    "default": True,
                },
            },
        },
    }


def _docs_tool_definition(mindset: Any) -> dict[str, Any]:
    """Return docs tool definition."""
    return {
        "name": "review_docs",
        "description": f"""Analyze documentation coverage and quality.

{mindset.format_for_tool_description()}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_coverage": {
                    "type": "integer",
                    "description": "Minimum docstring coverage percentage (default: 80)",
                },
            },
        },
    }


def _perf_tool_definition(mindset: Any) -> dict[str, Any]:
    """Return perf tool definition."""
    return {
        "name": "review_perf",
        "description": f"""Analyze code for performance issues and patterns.

{mindset.format_for_tool_description()}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_profiling": {
                    "type": "boolean",
                    "description": "Whether to run test profiling (default: true)",
                    "default": True,
                },
            },
        },
    }


def _report_tool_definition() -> dict[str, Any]:
    """Return report tool definition."""
    return {
        "name": "review_report",
        "description": "Generate consolidated report from all analysis results with overall verdict.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    }


def _all_tool_definition() -> dict[str, Any]:
    """Return review_all tool definition."""
    return {
        "name": "review_all",
        "description": """Run complete code review (scope + quality + security + deps + docs + perf + report).

Combines all review tools with their respective mindsets for comprehensive analysis.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["git", "full"],
                    "description": "Scan mode",
                    "default": "git",
                },
                "complexity_threshold": {
                    "type": "integer",
                    "description": "Maximum cyclomatic complexity",
                },
                "severity_threshold": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Minimum security severity",
                    "default": "low",
                },
            },
        },
    }
