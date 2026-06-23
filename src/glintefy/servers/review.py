"""MCP Server for code review operations.

This module implements an MCP server that exposes the review sub-servers
(scope, quality, security) as MCP tools.

The server uses stderr for logging (MCP protocol uses stdout for messages).
"""

from pathlib import Path
from typing import Any

from glintefy.config import get_config, get_max_workers
from glintefy.subservers.common.logging import (
    debug_log,
    get_mcp_logger,
    log_debug,
    log_error_detailed,
    log_tool_execution,
)
from glintefy.subservers.review.cache_subserver import CacheSubServer
from glintefy.subservers.review.deps import DepsSubServer
from glintefy.subservers.review.docs import DocsSubServer
from glintefy.subservers.review.perf import PerfSubServer
from glintefy.subservers.review.quality import QualitySubServer
from glintefy.subservers.review.report import ReportSubServer
from glintefy.subservers.review.scope import ScopeSubServer
from glintefy.subservers.review.security import SecuritySubServer

# Initialize MCP logger (stderr only)
logger = get_mcp_logger("glintefy.servers.review")

# Default output directory (can be overridden by config)
DEFAULT_OUTPUT_DIR = "LLM-CONTEXT/glintefy/review"


class ReviewMCPServer:
    """MCP Server for code review operations.

    Exposes the following tools:
    - review_scope: Determine files to review
    - review_quality: Analyze code quality
    - review_security: Scan for security vulnerabilities
    - review_all: Run all review sub-servers

    All logging goes to stderr (MCP protocol uses stdout).
    """

    # Default subservers to run (in order)
    DEFAULT_SUBSERVERS = ["scope", "quality", "security", "deps", "docs", "perf"]

    def __init__(self, repo_path: Path | None = None):
        """Initialize the review MCP server.

        Args:
            repo_path: Repository path to analyze (default: current directory)
        """
        self.repo_path = repo_path or Path.cwd()

        # Load configuration
        config = get_config(start_dir=str(self.repo_path))
        review_config = config.get("review", {})

        # Output directory
        output_dir = review_config.get("output_dir", DEFAULT_OUTPUT_DIR)
        self._output_base = self.repo_path / output_dir

        # Configurable subserver list and behavior
        self._subservers = review_config.get("subservers", self.DEFAULT_SUBSERVERS)
        self._stop_on_failure = review_config.get("stop_on_failure", False)

        log_debug(
            logger,
            "ReviewMCPServer initialized",
            repo_path=str(self.repo_path),
            output_base=str(self._output_base),
            subservers=self._subservers,
            stop_on_failure=self._stop_on_failure,
        )

    @debug_log(logger)
    def run_scope(
        self,
        mode: str = "git",
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Run scope analysis to determine files to review.

        Args:
            mode: "git" for uncommitted changes (default), "full" for all files
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/scope)

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        output = output_dir or self._output_base / "scope"

        server = ScopeSubServer(
            output_dir=output,
            repo_path=self.repo_path,
            mode=mode,
            mcp_mode=True,  # Use stderr logging
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "scope", result.metrics.get("total_files", 0), result.status, duration_ms=duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_quality(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        complexity_threshold: int | None = None,
        maintainability_threshold: int | None = None,
    ) -> dict[str, Any]:
        """Run quality analysis on code files.

        Args:
            input_dir: Input directory with files list (default: scope output)
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/quality)
            complexity_threshold: Override complexity threshold
            maintainability_threshold: Override maintainability threshold

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        input_path = input_dir or self._output_base / "scope"
        output_path = output_dir or self._output_base / "quality"

        server = QualitySubServer(
            input_dir=input_path,
            output_dir=output_path,
            repo_path=self.repo_path,
            complexity_threshold=complexity_threshold,
            maintainability_threshold=maintainability_threshold,
            mcp_mode=True,  # Use stderr logging
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "quality", result.metrics.get("files_analyzed", 0), result.status, result.metrics.get("issues_count", 0), duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_security(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        severity_threshold: str = "low",
        confidence_threshold: str = "low",
        critical_threshold: int | None = None,
        warning_threshold: int | None = None,
    ) -> dict[str, Any]:
        """Run security analysis on code files.

        Args:
            input_dir: Input directory with files list (default: scope output)
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/security)
            severity_threshold: Minimum severity ("low", "medium", "high")
            confidence_threshold: Minimum confidence ("low", "medium", "high")
            critical_threshold: Number of high severity issues to trigger PARTIAL status
            warning_threshold: Number of medium severity issues to trigger PARTIAL status

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        input_path = input_dir or self._output_base / "scope"
        output_path = output_dir or self._output_base / "security"

        server = SecuritySubServer(
            input_dir=input_path,
            output_dir=output_path,
            repo_path=self.repo_path,
            severity_threshold=severity_threshold,
            confidence_threshold=confidence_threshold,
            critical_threshold=critical_threshold,
            warning_threshold=warning_threshold,
            mcp_mode=True,  # Use stderr logging
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "security", result.metrics.get("files_scanned", 0), result.status, result.metrics.get("issues_found", 0), duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_deps(
        self,
        output_dir: Path | None = None,
        scan_vulnerabilities: bool = True,
        check_licenses: bool = True,
        check_outdated: bool = True,
    ) -> dict[str, Any]:
        """Run dependency analysis.

        Args:
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/deps)
            scan_vulnerabilities: Enable vulnerability scanning
            check_licenses: Enable license compliance checking
            check_outdated: Enable outdated package detection

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        output_path = output_dir or self._output_base / "deps"

        server = DepsSubServer(
            output_dir=output_path,
            repo_path=self.repo_path,
            scan_vulnerabilities=scan_vulnerabilities,
            check_licenses=check_licenses,
            check_outdated=check_outdated,
            mcp_mode=True,
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "deps", result.metrics.get("total_dependencies", 0), result.status, result.metrics.get("total_issues", 0), duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_docs(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        min_coverage: int | None = None,
        docstring_style: str | None = None,
    ) -> dict[str, Any]:
        """Run documentation analysis.

        Args:
            input_dir: Input directory with files list (default: scope output)
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/docs)
            min_coverage: Minimum docstring coverage percentage
            docstring_style: Expected docstring style format (google, numpy, sphinx)

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        input_path = input_dir or self._output_base / "scope"
        output_path = output_dir or self._output_base / "docs"

        server = DocsSubServer(
            input_dir=input_path,
            output_dir=output_path,
            repo_path=self.repo_path,
            min_coverage=min_coverage,
            docstring_style=docstring_style,
            mcp_mode=True,
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "docs", result.metrics.get("files_analyzed", 0), result.status, result.metrics.get("total_issues", 0), duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_perf(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        run_profiling: bool = True,
        nested_loop_threshold: int | None = None,
    ) -> dict[str, Any]:
        """Run performance analysis.

        Args:
            input_dir: Input directory with files list (default: scope output)
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/perf)
            run_profiling: Whether to run test profiling
            nested_loop_threshold: Nesting depth to trigger warning (2=O(n^2), 3=O(n^3))

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        input_path = input_dir or self._output_base / "scope"
        output_path = output_dir or self._output_base / "perf"

        server = PerfSubServer(
            input_dir=input_path,
            output_dir=output_path,
            repo_path=self.repo_path,
            run_profiling=run_profiling,
            nested_loop_threshold=nested_loop_threshold,
            mcp_mode=True,
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "perf", result.metrics.get("files_analyzed", 0), result.status, result.metrics.get("total_issues", 0), duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_cache(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        cache_size: int | None = None,
        hit_rate_threshold: float | None = None,
        speedup_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Run cache analysis.

        Args:
            input_dir: Input directory with scope + perf results
            output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/cache)
            cache_size: Override cache size
            hit_rate_threshold: Override hit rate threshold
            speedup_threshold: Override speedup threshold

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        input_path = input_dir or self._output_base / "scope"
        output_path = output_dir or self._output_base / "cache"

        server = CacheSubServer(
            input_dir=input_path,
            output_dir=output_path,
            repo_path=self.repo_path,
            cache_size=cache_size,
            hit_rate_threshold=hit_rate_threshold,
            speedup_threshold=speedup_threshold,
            mcp_mode=True,
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(
            logger,
            "cache",
            result.metrics.get("cache_candidates", 0),
            result.status,
            result.metrics.get("recommendations", 0),
            duration_ms,
        )

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_report(self) -> dict[str, Any]:
        """Generate consolidated report from all analysis results.

        Returns:
            Dictionary with status, summary, metrics, and artifact paths
        """
        output_path = self._output_base / "report"

        server = ReportSubServer(
            input_dir=self._output_base,
            output_dir=output_path,
            repo_path=self.repo_path,
            mcp_mode=True,
        )

        import time

        start = time.perf_counter()
        result = server.run()
        duration_ms = (time.perf_counter() - start) * 1000

        log_tool_execution(logger, "report", 0, result.status, 0, duration_ms)

        return {
            "status": result.status,
            "summary": result.summary,
            "metrics": result.metrics,
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "errors": result.errors,
        }

    @debug_log(logger)
    def run_all(
        self,
        mode: str = "git",
        complexity_threshold: int | None = None,
        severity_threshold: str = "low",
    ) -> dict[str, Any]:
        """Run all review sub-servers.

        Execution order:
        1. Scope (sequential, required by others)
        2. Quality, security, deps, docs, perf (parallel)
        3. Cache (sequential, modifies source files)
        4. Report (sequential, consolidates results)

        Note: Cache runs sequentially after parallel analyses because it
        modifies source files, which would interfere with other sub-servers
        if run in parallel.

        Args:
            mode: Scope mode ("git" for uncommitted changes, "full" for all files)
            complexity_threshold: Override for quality analysis
            severity_threshold: Override for security analysis

        Returns:
            Combined results from all sub-servers
        """
        log_debug(logger, "Starting full review", mode=mode)

        results = self._init_results()

        # Step 1: Run scope first (required by other sub-servers)
        if not self._run_scope_step(results, mode):
            return results

        # Step 2: Run quality, security, deps, docs, perf in parallel
        self._run_parallel_analyses(results, complexity_threshold, severity_threshold)

        # Step 3: Run cache analysis (sequential, after parallel analyses)
        self._run_cache_step(results)

        # Step 4: Generate consolidated report
        self._run_report_step(results)

        # Determine final status
        self._determine_final_status(results)

        log_debug(logger, "Full review complete", status=results["overall_status"], errors=len(results["errors"]))

        return results

    def _init_results(self) -> dict[str, Any]:
        """Initialize results dictionary with skip reasons for unconfigured subservers."""
        all_subservers = ["scope", "quality", "security", "deps", "docs", "perf", "cache"]
        results: dict[str, Any] = {
            "overall_status": "SUCCESS",
            "report": None,
            "errors": [],
        }

        # Initialize each subserver - mark as skipped if not configured
        for name in all_subservers:
            if name in self._subservers:
                results[name] = None  # Will be populated when run
            else:
                results[name] = {
                    "status": "NOT_RUN",
                    "skip_reason": f"'{name}' not in configured subservers (check review.subservers in config)",
                    "metrics": {},
                    "issues": [],
                }

        return results

    def _run_scope_step(self, results: dict[str, Any], mode: str) -> bool:
        """Run scope analysis. Returns False if failed."""
        try:
            results["scope"] = self.run_scope(mode=mode)
            if results["scope"]["status"] == "FAILED":
                results["overall_status"] = "FAILED"
                results["errors"].append("Scope analysis failed")
                return False
            return True
        except Exception as e:
            log_error_detailed(logger, e, context={"step": "scope"})
            results["overall_status"] = "FAILED"
            results["errors"].append(f"Scope error: {e}")
            return False

    def _run_parallel_analyses(
        self,
        results: dict[str, Any],
        complexity_threshold: int | None,
        severity_threshold: str,
    ) -> None:
        """Run configured subservers (except scope) in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def make_task(name: str, runner: Any) -> Any:
            """Create a task function for parallel execution."""

            def task() -> tuple[str, dict[str, Any], str | None]:
                """Execute the analysis task and return results."""
                try:
                    result = runner()
                    error = f"{name.title()} analysis failed" if result["status"] == "FAILED" else None
                    return (name, result, error)
                except Exception as e:
                    log_error_detailed(logger, e, context={"step": name})
                    error_result = {
                        "status": "FAILED",
                        "skip_reason": f"Exception during {name} analysis: {e}",
                        "metrics": {},
                        "issues": [],
                    }
                    return (name, error_result, f"{name.title()} error: {e}")

            return task

        # Build task list based on configured subservers (skip 'scope' - runs first)
        subserver_runners = {
            "quality": lambda: self.run_quality(complexity_threshold=complexity_threshold),
            "security": lambda: self.run_security(severity_threshold=severity_threshold),
            "deps": self.run_deps,
            "docs": self.run_docs,
            "perf": self.run_perf,
        }

        tasks = []
        for name in self._subservers:
            if name == "scope":
                continue  # Scope runs first, not in parallel
            if name in subserver_runners:
                tasks.append(make_task(name, subserver_runners[name]))

        if not tasks:
            return

        max_workers = get_max_workers(start_dir=str(self.repo_path))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(task) for task in tasks]
            for future in as_completed(futures):
                name, result, error = future.result()
                results[name] = result
                if error:
                    results["overall_status"] = "PARTIAL"
                    results["errors"].append(error)
                    if self._stop_on_failure:
                        # Cancel remaining futures and exit
                        for f in futures:
                            f.cancel()
                        return

    def _run_cache_step(self, results: dict[str, Any]) -> None:
        """Run cache analysis (sequential, modifies source files).

        Only runs if 'cache' is in the configured subservers list.
        Cache always runs last and sequentially because it modifies source files.
        """
        if "cache" not in self._subservers:
            return  # Already marked as skipped in _init_results

        try:
            results["cache"] = self.run_cache()
            if results["cache"]["status"] == "FAILED":
                results["overall_status"] = "PARTIAL"
                results["errors"].append("Cache analysis failed")
        except Exception as e:
            log_error_detailed(logger, e, context={"step": "cache"})
            results["cache"] = {
                "status": "FAILED",
                "skip_reason": f"Exception during cache analysis: {e}",
                "metrics": {},
                "issues": [],
            }
            results["errors"].append(f"Cache error: {e}")

    def _run_report_step(self, results: dict[str, Any]) -> None:
        """Generate consolidated report."""
        try:
            results["report"] = self.run_report()
        except Exception as e:
            log_error_detailed(logger, e, context={"step": "report"})
            results["errors"].append(f"Report error: {e}")

    def _determine_final_status(self, results: dict[str, Any]) -> None:
        """Determine final status based on analysis results."""
        if results["overall_status"] != "SUCCESS":
            return

        quality_issues = results["quality"]["metrics"].get("critical_issues", 0) if results["quality"] else 0
        security_issues = results["security"]["metrics"].get("high_severity", 0) if results["security"] else 0

        if quality_issues > 0 or security_issues > 0:
            results["overall_status"] = "PARTIAL"

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get MCP tool definitions for this server.

        Tool descriptions include the reviewer mindset to guide the analysis.

        Returns:
            List of tool definition dictionaries for MCP protocol
        """
        from glintefy.servers.review_tools import get_review_tool_definitions

        return get_review_tool_definitions()

    def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle an MCP tool call.

        Uses dispatch pattern to avoid deep nesting.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        from glintefy.servers.review_handlers import handle_tool_call

        return handle_tool_call(self, name, arguments)
