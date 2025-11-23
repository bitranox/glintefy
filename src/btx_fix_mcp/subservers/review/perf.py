"""Perf sub-server: Performance analysis and profiling.

This sub-server analyzes code for performance issues:
- Function profiling with cProfile
- Hotspot detection
- Memory usage analysis
- Algorithm complexity warnings
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from btx_fix_mcp.config import get_config, get_display_limit, get_subserver_config, get_timeout
from btx_fix_mcp.subservers.common.chunked_writer import (
    cleanup_chunked_issues,
    write_chunked_issues,
)
from btx_fix_mcp.subservers.common.issues import (
    BaseIssue,
    HotspotIssue,
    PerformanceIssue,
    PerfMetrics,
)
from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_error_detailed,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from btx_fix_mcp.subservers.common.mindsets import (
    PERF_MINDSET,
    evaluate_results,
    get_mindset,
)


class PerfSubServer(BaseSubServer):
    """Performance analysis and profiling sub-server.

    Analyzes code for performance issues including:
    - Hotspot detection via profiling
    - Expensive operation patterns
    - Algorithm complexity issues
    - Memory-intensive patterns
    """

    # Patterns that may indicate performance issues
    EXPENSIVE_PATTERNS = [
        (r"for .+ in .+:\s*for .+ in .+:", "nested_loop", "Nested loop detected"),
        (r"\.append\(.+\) for .+ in", "list_append_loop", "List append in loop"),
        (r"import re\n.*re\.(match|search|findall)\(", "regex_compile", "Regex not precompiled"),
        (r"open\(.+\)\.read\(\)", "file_read_all", "Reading entire file into memory"),
        (r"json\.loads\(.*\.read\(\)\)", "json_load_memory", "Loading JSON into memory"),
        (r"\+ ['\"]=", "string_concat_loop", "String concatenation (use join)"),
    ]

    def __init__(
        self,
        name: str = "perf",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        run_profiling: bool | None = None,
        profile_tests: bool | None = None,
        detect_patterns: bool | None = None,
        mcp_mode: bool = False,
    ):
        """Initialize perf sub-server."""
        # Get output base from config for standalone use
        base_config = get_config(start_dir=str(repo_path or Path.cwd()))
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/btx_fix_mcp/review")

        if input_dir is None:
            input_dir = Path.cwd() / output_base / "scope"
        if output_dir is None:
            output_dir = Path.cwd() / output_base / name

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mcp_mode = mcp_mode

        # Initialize logger
        if mcp_mode:
            self.logger = get_mcp_logger(f"btx_fix_mcp.{name}")
        else:
            self.logger = setup_logger(name, log_file=None, level=20)

        # Load config
        config = get_subserver_config("perf", start_dir=str(self.repo_path))
        self.config = config

        # Load reviewer mindset
        self.mindset = get_mindset(PERF_MINDSET, config)

        # Feature flags
        self.run_profiling = run_profiling if run_profiling is not None else config.get("run_profiling", True)
        self.profile_tests = profile_tests if profile_tests is not None else config.get("profile_tests", True)
        self.detect_patterns = detect_patterns if detect_patterns is not None else config.get("detect_patterns", True)

        # Thresholds
        self.hotspot_threshold = config.get("hotspot_threshold", 5.0)  # % of total time
        self.min_improvement = config.get("min_improvement", 5.0)  # % improvement to justify

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for performance analysis."""
        missing = []

        # Check for files to analyze
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(f"No files list found in {self.input_dir}. Run scope sub-server first.")

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute performance analysis."""
        log_section(self.logger, "PERFORMANCE ANALYSIS")

        try:
            results: dict[str, Any] = {
                "hotspots": [],
                "pattern_issues": [],
                "profile_data": {},
                "test_timing": {},
            }
            all_issues: list[BaseIssue] = []

            # Step 1: Get files to analyze
            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()

            if not python_files:
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Performance Analysis\n\nNo Python files to analyze.",
                    artifacts={},
                    metrics={"files_analyzed": 0},
                )

            # Step 2: Pattern-based detection
            if self.detect_patterns:
                log_step(self.logger, 2, "Detecting performance anti-patterns")
                with LogContext(self.logger, "Pattern detection"):
                    pattern_issues = self._detect_patterns(python_files)
                    results["pattern_issues"] = pattern_issues
                    all_issues.extend(pattern_issues)

            # Step 3: Run profiling if enabled
            if self.run_profiling and self.profile_tests:
                log_step(self.logger, 3, "Running test suite profiling")
                with LogContext(self.logger, "Test profiling"):
                    profile_results = self._profile_tests()
                    results["profile_data"] = profile_results.get("profile", {})
                    results["hotspots"] = profile_results.get("hotspots", [])
                    results["test_timing"] = profile_results.get("timing", {})
                    all_issues.extend(self._hotspots_to_issues(results["hotspots"]))

            # Step 4: Analyze complexity patterns
            log_step(self.logger, 4, "Analyzing algorithmic complexity")
            with LogContext(self.logger, "Complexity analysis"):
                complexity_issues = self._analyze_complexity(python_files)
                all_issues.extend(complexity_issues)

            # Step 5: Save results
            log_step(self.logger, 5, "Saving results")
            artifacts = self._save_results(results, all_issues)

            # Step 6: Generate summary
            summary = self._generate_summary(results, all_issues, python_files)

            # Determine status
            critical_count = len([i for i in all_issues if i.severity == "critical"])
            status = "SUCCESS" if critical_count == 0 else "PARTIAL"

            log_result(self.logger, status == "SUCCESS", f"Analysis complete: {len(all_issues)} issues found")

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=self._compile_metrics(python_files, results, all_issues),
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
                summary=f"# Performance Analysis Failed\n\n**Error**: {e}",
                artifacts={},
                errors=[str(e)],
            )

    def _get_python_files(self) -> list[str]:
        """Get Python files to analyze."""
        files_list = self.input_dir / "files_code.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []
        all_files = files_list.read_text().strip().split("\n")
        python_files = [f for f in all_files if f.endswith(".py") and f]
        return [str(self.repo_path / f) for f in python_files]

    def _detect_patterns(self, files: list[str]) -> list[PerformanceIssue]:
        """Detect performance anti-patterns in code."""
        import re

        issues: list[PerformanceIssue] = []

        for file_path in files:
            try:
                content = Path(file_path).read_text()
                lines = content.split("\n")

                for pattern, issue_type, message in self.EXPENSIVE_PATTERNS:
                    for match in re.finditer(pattern, content):
                        line_num = content[: match.start()].count("\n") + 1
                        issues.append(
                            PerformanceIssue(
                                type=issue_type,
                                severity="warning",
                                file=file_path,
                                line=line_num,
                                message=message,
                                pattern=pattern,
                            )
                        )

                # Check for O(n²) patterns
                for i, line in enumerate(lines, 1):
                    if "for " in line and "range(len(" in line:
                        issues.append(
                            PerformanceIssue(
                                type="range_len",
                                severity="warning",
                                file=file_path,
                                line=i,
                                message="Using range(len()) - consider enumerate() or direct iteration",
                            )
                        )

            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        return issues

    def _profile_tests(self) -> dict[str, Any]:
        """Run tests with profiling enabled."""
        results = {"profile": {}, "hotspots": [], "timing": {}}

        tests_dir = self.repo_path / "tests"
        if not tests_dir.exists():
            self.logger.info("No tests directory found")
            return results

        try:
            # Run pytest with profiling
            timeout = get_timeout("profile_tests", 300, start_dir=str(self.repo_path))
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=no", "-q", "--durations=10"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.repo_path),
            )

            results["timing"]["raw_output"] = result.stdout

            # Parse slow tests from --durations output
            for line in result.stdout.split("\n"):
                if "s call" in line or "s setup" in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            duration = float(parts[0].rstrip("s"))
                            test_name = parts[-1] if len(parts) > 1 else "unknown"
                            if duration > 1.0:  # Tests taking > 1 second
                                results["hotspots"].append(
                                    {
                                        "name": test_name,
                                        "duration": duration,
                                        "type": "slow_test",
                                    }
                                )
                        except ValueError:
                            pass

        except FileNotFoundError:
            self.logger.info("pytest not available")
        except subprocess.TimeoutExpired:
            self.logger.warning("Test profiling timed out")
        except Exception as e:
            self.logger.warning(f"Profiling error: {e}")

        return results

    def _analyze_complexity(self, files: list[str]) -> list[PerformanceIssue]:
        """Analyze algorithmic complexity patterns."""
        issues: list[PerformanceIssue] = []

        for file_path in files:
            try:
                content = Path(file_path).read_text()

                # Check for potential O(n²) or worse patterns
                if content.count("for ") >= 2:
                    # Nested loops indicator
                    lines = content.split("\n")
                    indent_stack = []

                    for i, line in enumerate(lines, 1):
                        stripped = line.lstrip()
                        if stripped.startswith("for ") or stripped.startswith("while "):
                            current_indent = len(line) - len(stripped)
                            # Check if nested
                            if indent_stack and current_indent > indent_stack[-1]:
                                issues.append(
                                    PerformanceIssue(
                                        type="nested_iteration",
                                        severity="warning",
                                        file=file_path,
                                        line=i,
                                        message="Nested iteration detected - potential O(n²) complexity",
                                    )
                                )
                            indent_stack.append(current_indent)

            except Exception as e:
                self.logger.warning(f"Error analyzing complexity in {file_path}: {e}")

        return issues

    def _hotspots_to_issues(self, hotspots: list[dict]) -> list[HotspotIssue]:
        """Convert hotspots to issues."""
        issues: list[HotspotIssue] = []
        for hs in hotspots:
            duration = hs.get("duration", 0)
            if duration > 5.0:  # Very slow
                severity = "critical"
            elif duration > 2.0:
                severity = "warning"
            else:
                continue

            issues.append(
                HotspotIssue(
                    type="slow_test",
                    severity=severity,
                    function=hs.get("name", "unknown"),
                    time_percent=duration,
                    message=f"Slow test: {hs.get('name', 'unknown')} takes {duration:.2f}s",
                )
            )
        return issues

    def _save_results(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Path]:
        """Save all results to files."""
        artifacts = {}
        report_dir = self.output_dir.parent / "report"

        pattern_issues = results.get("pattern_issues", [])
        if pattern_issues:
            path = self.output_dir / "pattern_issues.json"
            pattern_dicts = [i.to_dict() if hasattr(i, "to_dict") else i for i in pattern_issues]
            path.write_text(json.dumps(pattern_dicts, indent=2))
            artifacts["pattern_issues"] = path

        if results.get("hotspots"):
            path = self.output_dir / "hotspots.json"
            path.write_text(json.dumps(results["hotspots"], indent=2))
            artifacts["hotspots"] = path

        if results.get("test_timing"):
            path = self.output_dir / "test_timing.json"
            path.write_text(json.dumps(results["test_timing"], indent=2))
            artifacts["test_timing"] = path

        if all_issues:
            # Convert to dicts
            issues_dicts = [i.to_dict() for i in all_issues]

            # Get unique issue types
            issue_types = list({issue.get("type", "unknown") for issue in issues_dicts})

            # Cleanup old chunked files
            cleanup_chunked_issues(
                output_dir=report_dir,
                issue_types=issue_types,
                prefix="issues",
            )

            # Write chunked issues
            written_files = write_chunked_issues(
                issues=issues_dicts,
                output_dir=report_dir,
                prefix="issues",
            )

            if written_files:
                artifacts["issues"] = written_files[0]

        return artifacts

    def _compile_metrics(self, files: list[str], results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Any]:
        """Compile metrics for result."""
        return PerfMetrics(
            files_analyzed=len(files),
            patterns_found=len(results.get("pattern_issues", [])),
            hotspots_found=len(results.get("hotspots", [])),
            total_issues=len(all_issues),
        ).model_dump()

    def _generate_summary(self, results: dict[str, Any], all_issues: list[BaseIssue], files: list[str]) -> str:
        """Generate markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(files, results, all_issues)

        # Evaluate with mindset (convert to dicts for evaluate_results)
        critical_issues = [i.to_dict() for i in all_issues if i.severity == "critical"]
        warning_issues = [i.to_dict() for i in all_issues if i.severity == "warning"]

        verdict = evaluate_results(
            self.mindset,
            critical_issues,
            warning_issues,
            max(len(files), 1),
        )

        lines = [
            "# Performance Analysis Report",
            "",
            "## Reviewer Mindset",
            "",
            self.mindset.format_header(),
            "",
            self.mindset.format_approach(),
            "",
            "## Verdict",
            "",
            f"**{verdict.verdict_text}**",
            "",
            f"- Critical issues: {verdict.critical_count}",
            f"- Warnings: {verdict.warning_count}",
            f"- Files analyzed: {len(files)}",
            "",
            "## Overview",
            "",
            f"**Files Analyzed**: {metrics['files_analyzed']}",
            f"**Pattern Issues**: {metrics['patterns_found']}",
            f"**Performance Hotspots**: {metrics['hotspots_found']}",
            f"**Total Issues**: {metrics['total_issues']}",
            "",
        ]

        # Hotspots
        hotspots = results.get("hotspots", [])
        if hotspots:
            limit = get_display_limit("max_hotspots", 10, start_dir=str(self.repo_path))
            display_count = len(hotspots) if limit is None else min(limit, len(hotspots))

            header = "## Performance Hotspots" if limit is None else f"## Performance Hotspots (showing {display_count} of {len(hotspots)})"
            lines.extend([header, ""])

            for hs in hotspots[:limit]:
                lines.append(f"- **{hs.get('name', 'unknown')}**: {hs.get('duration', 0):.2f}s")

            if limit is not None and len(hotspots) > limit:
                lines.append("")
                lines.append(f"*Note: {len(hotspots) - limit} more hotspots not shown. Set `output.display.max_hotspots = 0` in config for unlimited display.*")
            lines.append("")

        # Pattern issues
        pattern_issues = results.get("pattern_issues", [])
        if pattern_issues:
            limit = get_display_limit("max_pattern_issues", 10, start_dir=str(self.repo_path))
            display_count = len(pattern_issues) if limit is None else min(limit, len(pattern_issues))

            header = "## Anti-Pattern Detections" if limit is None else f"## Anti-Pattern Detections (showing {display_count} of {len(pattern_issues)})"
            lines.extend([header, ""])

            for issue in pattern_issues[:limit]:
                file_path = issue.file if hasattr(issue, "file") else issue.get("file", "")
                line_num = issue.line if hasattr(issue, "line") else issue.get("line", 0)
                message = issue.message if hasattr(issue, "message") else issue.get("message", "")
                lines.append(f"- `{file_path}:{line_num}` - {message}")

            if limit is not None and len(pattern_issues) > limit:
                lines.append("")
                lines.append(
                    f"*Note: {len(pattern_issues) - limit} more pattern issues not shown. Set `output.display.max_pattern_issues = 0` in config for unlimited display.*"
                )
            lines.append("")

        # Approval status
        lines.extend(["## Approval Status", ""])
        lines.append(f"**{verdict.verdict_text}**")
        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)
