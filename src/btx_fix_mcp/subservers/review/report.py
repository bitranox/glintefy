"""Report sub-server: Consolidated report generation.

This sub-server compiles results from all analysis sub-servers into
a comprehensive final report with overall verdict.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from btx_fix_mcp.config import get_config, get_display_limit
from btx_fix_mcp.subservers.common.chunked_writer import (
    cleanup_all_issues,
    write_chunked_all_issues,
)
from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.logging import (
    get_mcp_logger,
    log_error_detailed,
    log_result,
    log_section,
    log_step,
    setup_logger,
)

# Verdict status types
VerdictStatus = Literal["APPROVED", "APPROVED_WITH_COMMENTS", "NEEDS_WORK", "REJECTED", "REVIEW_INCOMPLETE"]


class Verdict(BaseModel):
    """Overall code review verdict.

    Attributes:
        status: Review outcome status
        message: Human-readable verdict message with emoji
        recommendations: List of actionable recommendations
    """

    model_config = ConfigDict(extra="forbid")

    status: VerdictStatus
    message: str
    recommendations: list[str] = Field(default_factory=list)


class ReportMetrics(BaseModel):
    """Aggregated metrics from all sub-servers.

    Attributes:
        timestamp: ISO format timestamp of report generation
        subservers_run: List of sub-servers that were executed
        subservers_passed: List of sub-servers that passed
        subservers_failed: List of sub-servers that failed
        total_issues: Total count of all issues
        critical_issues: Count of critical/error severity issues
        warning_issues: Count of warning severity issues
        files_analyzed: Number of files analyzed
    """

    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    subservers_run: list[str] = Field(default_factory=list)
    subservers_passed: list[str] = Field(default_factory=list)
    subservers_failed: list[str] = Field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    warning_issues: int = 0
    files_analyzed: int = 0


class ReportSubServer(BaseSubServer):
    """Consolidated report generator.

    Compiles results from all analysis sub-servers into a single
    comprehensive report with overall verdict and recommendations.
    """

    # Sub-servers to include in report (in order)
    SUBSERVERS = ["scope", "quality", "security", "deps", "docs", "perf"]

    def __init__(
        self,
        name: str = "report",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        mcp_mode: bool = False,
    ):
        """Initialize report sub-server."""
        # Get output base from config for standalone use
        base_config = get_config(start_dir=str(repo_path or Path.cwd()))
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/btx_fix_mcp/review")

        if input_dir is None:
            input_dir = Path.cwd() / output_base
        if output_dir is None:
            output_dir = Path.cwd() / output_base / name

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mcp_mode = mcp_mode
        self.review_base = input_dir

        # Initialize logger
        if mcp_mode:
            self.logger = get_mcp_logger(f"btx_fix_mcp.{name}")
        else:
            self.logger = setup_logger(name, log_file=None, level=20)

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for report generation."""
        missing = []

        # Check that at least one sub-server has run
        found_any = False
        for subserver in self.SUBSERVERS:
            status_file = self.review_base / subserver / "status.txt"
            if status_file.exists():
                found_any = True
                break

        if not found_any:
            missing.append("No analysis results found. Run at least one analysis sub-server first.")

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute report generation."""
        log_section(self.logger, "REPORT GENERATION")

        try:
            # Step 1: Gather results from all sub-servers
            log_step(self.logger, 1, "Gathering analysis results")
            subserver_results = self._gather_results()

            # Step 2: Compile overall metrics
            log_step(self.logger, 2, "Compiling metrics")
            overall_metrics = self._compile_overall_metrics(subserver_results)

            # Step 3: Determine overall verdict
            log_step(self.logger, 3, "Determining overall verdict")
            verdict = self._determine_verdict(subserver_results, overall_metrics)

            # Step 4: Generate consolidated report
            log_step(self.logger, 4, "Generating report")
            report = self._generate_report(subserver_results, overall_metrics, verdict)

            # Step 5: Save report
            log_step(self.logger, 5, "Saving report")
            artifacts = self._save_report(report, subserver_results, overall_metrics, verdict)

            log_result(self.logger, True, f"Report generated: {verdict.status}")

            return SubServerResult(
                status="SUCCESS",
                summary=report,
                artifacts=artifacts,
                metrics=overall_metrics.model_dump(),
            )

        except Exception as e:
            log_error_detailed(
                self.logger,
                e,
                context={"repo_path": str(self.repo_path)},
                include_traceback=True,
            )
            return SubServerResult(
                status="FAILED",
                summary=f"# Report Generation Failed\n\n**Error**: {e}",
                artifacts={},
                errors=[str(e)],
            )

    def _gather_results(self) -> dict[str, dict[str, Any]]:
        """Gather results from all sub-servers."""
        results = {}

        for subserver in self.SUBSERVERS:
            subserver_dir = self.review_base / subserver
            if not subserver_dir.exists():
                continue

            result: dict[str, Any] = {
                "status": "NOT_RUN",
                "summary": "",
                "metrics": {},
                "issues": [],
            }

            # Read status
            status_file = subserver_dir / "status.txt"
            if status_file.exists():
                result["status"] = status_file.read_text().strip()

            # Read summary
            summary_file = subserver_dir / f"{subserver}_summary.md"
            if summary_file.exists():
                result["summary"] = summary_file.read_text()

            # Read result.json for metrics
            result_file = subserver_dir / "result.json"
            if result_file.exists():
                try:
                    data = json.loads(result_file.read_text())
                    result["metrics"] = data.get("metrics", {})
                except json.JSONDecodeError:
                    pass

            # Read issues
            issues_file = subserver_dir / "issues.json"
            if issues_file.exists():
                try:
                    result["issues"] = json.loads(issues_file.read_text())
                except json.JSONDecodeError:
                    pass

            results[subserver] = result

        return results

    def _compile_overall_metrics(self, results: dict[str, dict]) -> ReportMetrics:
        """Compile overall metrics from all sub-servers."""
        metrics = ReportMetrics()

        for name, result in results.items():
            self._update_subserver_status(name, result, metrics)
            self._aggregate_issues(result, metrics)
            self._aggregate_files_analyzed(result, metrics)

        return metrics

    def _update_subserver_status(self, name: str, result: dict, metrics: ReportMetrics) -> None:
        """Update sub-server run/pass/fail status."""
        status = result["status"]

        if status == "NOT_RUN":
            return

        metrics.subservers_run.append(name)

        if status == "SUCCESS":
            metrics.subservers_passed.append(name)
        elif status == "FAILED":
            metrics.subservers_failed.append(name)

    def _aggregate_issues(self, result: dict, metrics: ReportMetrics) -> None:
        """Aggregate issue counts by severity."""
        for issue in result.get("issues", []):
            metrics.total_issues += 1
            severity = issue.get("severity", "").lower()

            if severity in ("critical", "error"):
                metrics.critical_issues += 1
            elif severity == "warning":
                metrics.warning_issues += 1

    def _aggregate_files_analyzed(self, result: dict, metrics: ReportMetrics) -> None:
        """Aggregate maximum files analyzed count."""
        sub_metrics = result.get("metrics", {})
        if "files_analyzed" in sub_metrics:
            metrics.files_analyzed = max(metrics.files_analyzed, sub_metrics["files_analyzed"])

    def _determine_verdict(self, results: dict[str, dict], metrics: ReportMetrics) -> Verdict:
        """Determine overall verdict."""
        verdict = Verdict(
            status="APPROVED",
            message="✅ Code review passed - no critical issues found",
        )

        # Check for failures
        if metrics.subservers_failed:
            verdict.status = "REVIEW_INCOMPLETE"
            verdict.message = f"⚠️ Review incomplete - {len(metrics.subservers_failed)} sub-servers failed"
            verdict.recommendations.append("Fix sub-server failures and re-run analysis")

        # Check for critical issues
        if metrics.critical_issues > 0:
            verdict.status = "REJECTED"
            verdict.message = f"❌ Code review failed - {metrics.critical_issues} critical issues found"
            verdict.recommendations.append("Address all critical issues before merging")

        # Check individual sub-server verdicts
        security_result = results.get("security", {})
        if security_result.get("metrics", {}).get("high_severity", 0) > 0:
            if verdict.status == "APPROVED":
                verdict.status = "NEEDS_WORK"
                verdict.message = "🔧 Code review needs work - security issues found"
            verdict.recommendations.append("Fix security vulnerabilities")

        deps_result = results.get("deps", {})
        if deps_result.get("metrics", {}).get("vulnerabilities_count", 0) > 0:
            if verdict.status == "APPROVED":
                verdict.status = "NEEDS_WORK"
                verdict.message = "🔧 Code review needs work - dependency vulnerabilities found"
            verdict.recommendations.append("Update vulnerable dependencies")

        # Check for many warnings
        if metrics.warning_issues > 20 and verdict.status == "APPROVED":
            verdict.status = "APPROVED_WITH_COMMENTS"
            verdict.message = f"⚠️ Approved with comments - {metrics.warning_issues} warnings to address"

        return verdict

    def _generate_report(
        self,
        results: dict[str, dict],
        metrics: ReportMetrics,
        verdict: Verdict,
    ) -> str:
        """Generate consolidated markdown report."""
        lines = []
        lines.extend(self._format_header(metrics, verdict))
        lines.extend(self._format_summary_statistics(metrics))
        lines.extend(self._format_subserver_results(results))
        lines.extend(self._format_critical_issues(results))
        lines.extend(self._format_footer())
        return "\n".join(lines)

    def _format_header(self, metrics: ReportMetrics, verdict: Verdict) -> list[str]:
        """Format report header with verdict."""
        lines = [
            "# Code Review Report",
            "",
            f"**Generated**: {metrics.timestamp}",
            "",
            "---",
            "",
            "## Overall Verdict",
            "",
            f"### {verdict.message}",
            "",
            f"**Status**: `{verdict.status}`",
            "",
        ]

        if verdict.recommendations:
            lines.append("**Recommendations:**")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return lines

    def _format_summary_statistics(self, metrics: ReportMetrics) -> list[str]:
        """Format summary statistics section."""
        return [
            "---",
            "",
            "## Summary Statistics",
            "",
            f"- **Sub-servers run**: {len(metrics.subservers_run)}",
            f"- **Sub-servers passed**: {len(metrics.subservers_passed)}",
            f"- **Sub-servers failed**: {len(metrics.subservers_failed)}",
            f"- **Files analyzed**: {metrics.files_analyzed}",
            f"- **Total issues**: {metrics.total_issues}",
            f"- **Critical issues**: {metrics.critical_issues}",
            f"- **Warnings**: {metrics.warning_issues}",
            "",
        ]

    def _format_subserver_results(self, results: dict[str, dict]) -> list[str]:
        """Format individual sub-server results section."""
        lines = ["---", "", "## Sub-Server Results", ""]

        for name in self.SUBSERVERS:
            lines.extend(self._format_single_subserver(name, results.get(name, {"status": "NOT_RUN"})))

        return lines

    def _format_single_subserver(self, name: str, result: dict) -> list[str]:
        """Format a single sub-server's results."""
        status = result["status"]
        status_icon = {
            "SUCCESS": "✅",
            "PARTIAL": "⚠️",
            "FAILED": "❌",
            "NOT_RUN": "⏭️",
        }.get(status, "❓")

        lines = [
            f"### {status_icon} {name.title()}",
            "",
            f"**Status**: `{status}`",
            "",
        ]

        # Show key metrics
        sub_metrics = result.get("metrics", {})
        if sub_metrics:
            limit = get_display_limit("max_metrics_display", 5, start_dir=str(self.repo_path))
            items = list(sub_metrics.items())

            lines.append("**Key Metrics:**")
            for key, value in items[:limit]:
                lines.append(f"- {key}: {value}")

            if limit is not None and len(items) > limit:
                lines.append(f"- ... and {len(items) - limit} more metrics")
            lines.append("")

        # Show issue count
        issues = result.get("issues", [])
        if issues:
            critical = len([i for i in issues if i.get("severity") in ("critical", "error")])
            warnings = len([i for i in issues if i.get("severity") == "warning"])
            lines.append(f"**Issues**: {len(issues)} ({critical} critical, {warnings} warnings)")
            lines.append("")

        return lines

    def _format_critical_issues(self, results: dict[str, dict]) -> list[str]:
        """Format critical issues summary section."""
        all_critical = []
        for name, result in results.items():
            for issue in result.get("issues", []):
                if issue.get("severity") in ("critical", "error"):
                    issue["source"] = name
                    all_critical.append(issue)

        if not all_critical:
            return []

        limit = get_display_limit("max_critical_display", 20, start_dir=str(self.repo_path))
        display_count = len(all_critical) if limit is None else min(limit, len(all_critical))

        header = "## Critical Issues (Must Fix)" if limit is None else f"## Critical Issues (Must Fix) - showing {display_count} of {len(all_critical)}"
        lines = ["---", "", header, ""]

        for issue in all_critical[:limit]:
            source = issue.get("source", "unknown")
            message = issue.get("message", "No description")
            file_info = f"`{issue.get('file', '')}:{issue.get('line', '')}`" if issue.get("file") else ""
            lines.append(f"- **[{source}]** {file_info} {message}")

        if limit is not None and len(all_critical) > limit:
            lines.append("")
            lines.append(
                f"*Note: {len(all_critical) - limit} more critical issues not shown. Set `output.display.max_critical_display = 0` in config for unlimited display.*"
            )
        lines.append("")

        return lines

    def _format_footer(self) -> list[str]:
        """Format report footer."""
        return [
            "---",
            "",
            "*Report generated by btx_fix_mcp Review MCP Server*",
        ]

    def _save_report(
        self,
        report: str,
        results: dict[str, dict],
        metrics: ReportMetrics,
        verdict: Verdict,
    ) -> dict[str, Path]:
        """Save report and data files."""
        artifacts = {}

        # Save markdown report
        report_path = self.output_dir / "code_review_report.md"
        report_path.write_text(report)
        artifacts["report"] = report_path

        # Save metrics JSON
        metrics_path = self.output_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics.model_dump(), indent=2))
        artifacts["metrics"] = metrics_path

        # Save verdict JSON
        verdict_path = self.output_dir / "verdict.json"
        verdict_path.write_text(json.dumps(verdict.model_dump(), indent=2))
        artifacts["verdict"] = verdict_path

        # Save all issues consolidated
        all_issues = []
        for name, result in results.items():
            for issue in result.get("issues", []):
                issue["source_subserver"] = name
                all_issues.append(issue)

        if all_issues:
            # Cleanup old chunked all_issues files
            cleanup_all_issues(output_dir=self.output_dir)

            # Write chunked all_issues files
            written_files = write_chunked_all_issues(
                all_issues=all_issues,
                output_dir=self.output_dir,
            )

            if written_files:
                artifacts["all_issues"] = written_files[0]

        return artifacts
