"""Security sub-server: Scan for security vulnerabilities.

This sub-server scans code for security issues using:
- Bandit (Python security linter)
- Pattern matching for common vulnerabilities
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from glintefy.config import get_config, get_display_limit, get_subserver_config, get_timeout
from glintefy.subservers.base import BaseSubServer, SubServerResult
from glintefy.subservers.common.chunked_writer import (
    cleanup_chunked_issues,
    write_chunked_issues,
)
from glintefy.subservers.common.issues import SecurityMetrics
from glintefy.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_error_detailed,
    log_file_list,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from glintefy.subservers.common.mindsets import (
    SECURITY_MINDSET,
    evaluate_results,
    get_mindset,
)


class BanditIssue(BaseModel):
    """Typed representation of a Bandit security issue."""

    model_config = ConfigDict(extra="ignore")

    filename: str = ""
    relative_file: str = ""
    line_number: int = 0
    col_offset: int = 0
    end_col_offset: int = 0
    issue_severity: str = "LOW"
    issue_confidence: str = "LOW"
    issue_text: str = ""
    test_id: str = ""
    test_name: str = ""
    line_range: list[int] = Field(default_factory=list)
    more_info: str = ""
    issue_cwe: dict[str, Any] = Field(default_factory=dict)
    code: str = ""
    type: str = "security"


class SecuritySubServer(BaseSubServer):
    """Scan code for security vulnerabilities.

    Uses Bandit to detect common security issues:
    - SQL injection
    - Command injection
    - Hardcoded passwords
    - Insecure cryptography
    - And many more...

    Args:
        name: Sub-server name (default: "security")
        input_dir: Input directory (containing files_to_review.txt from scope)
        output_dir: Output directory for results
        repo_path: Repository path (default: current directory)
        severity_threshold: Minimum severity to report ("low", "medium", "high")
        confidence_threshold: Minimum confidence ("low", "medium", "high")
        config_file: Path to config file
        bandit_config: Path to bandit config file (overrides config)
        skip_tests: List of test IDs to skip (e.g., ["B101", "B102"])
        exclude_paths: Additional paths to exclude from scan
        critical_threshold: Number of high severity issues to trigger CRITICAL status (default: 1)
        warning_threshold: Number of medium severity issues to trigger WARNING status (default: 5)

    Example:
        >>> server = SecuritySubServer(
        ...     input_dir=Path("LLM-CONTEXT/glintefy/review/scope"),
        ...     output_dir=Path("LLM-CONTEXT/glintefy/review/security"),
        ...     severity_threshold="medium",
        ...     skip_tests=["B101"],
        ...     exclude_paths=["**/tests/*"],
        ...     critical_threshold=2,
        ...     warning_threshold=10
        ... )
        >>> result = server.run()
    """

    SEVERITY_LEVELS = {"low": 1, "medium": 2, "high": 3}

    def _init_directories(self, input_dir: Path | None, output_dir: Path | None, name: str, repo_path: Path) -> tuple[Path, Path]:
        """Initialize input and output directories."""
        base_config = get_config(start_dir=str(repo_path))
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")

        resolved_input = input_dir if input_dir is not None else Path.cwd() / output_base / "scope"
        resolved_output = output_dir if output_dir is not None else Path.cwd() / output_base / name

        return resolved_input, resolved_output

    def _init_logger(self, name: str, mcp_mode: bool):
        """Initialize logger based on mode."""
        if mcp_mode:
            return get_mcp_logger(f"glintefy.{name}")
        return setup_logger(name, log_file=None, level=20)

    def _apply_threshold_overrides(
        self,
        severity_threshold: str,
        confidence_threshold: str,
        config: dict | None,
    ) -> tuple[str, str]:
        """Apply threshold parameter overrides."""
        severity = severity_threshold if severity_threshold != "low" or config is None else config.get("severity_threshold", "low")
        confidence = confidence_threshold if confidence_threshold != "low" or config is None else config.get("confidence_threshold", "low")
        return severity, confidence

    def _apply_bandit_overrides(
        self,
        bandit_config: str | None,
        skip_tests: list[str] | None,
        exclude_paths: list[str] | None,
        full_config: dict,
    ) -> tuple[str, list[str], list[str]]:
        """Apply bandit configuration overrides."""
        bandit_cfg = bandit_config or full_config.get("bandit_config", "")
        skip = skip_tests if skip_tests is not None else full_config.get("skip_tests", [])
        exclude = exclude_paths if exclude_paths is not None else full_config.get("exclude_paths", [])
        return bandit_cfg, skip, exclude

    def _apply_mindset_overrides(
        self,
        critical_threshold: int | None,
        warning_threshold: int | None,
        full_config: dict,
    ) -> tuple[int, int]:
        """Apply mindset threshold overrides."""
        critical = critical_threshold if critical_threshold is not None else full_config.get("critical_threshold", 1)
        warning = warning_threshold if warning_threshold is not None else full_config.get("warning_threshold", 5)
        return critical, warning

    def __init__(
        self,
        name: str = "security",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        severity_threshold: str = "low",
        confidence_threshold: str = "low",
        config_file: Path | None = None,
        mcp_mode: bool = False,
        bandit_config: str | None = None,
        skip_tests: list[str] | None = None,
        exclude_paths: list[str] | None = None,
        critical_threshold: int | None = None,
        warning_threshold: int | None = None,
    ):
        """Initialize security sub-server.

        Args:
            name: Sub-server name
            input_dir: Input directory (containing files_to_review.txt from scope)
            output_dir: Output directory for results
            repo_path: Repository path (default: current directory)
            severity_threshold: Minimum severity to report ("low", "medium", "high")
            confidence_threshold: Minimum confidence ("low", "medium", "high")
            config_file: Path to config file
            mcp_mode: If True, log to stderr only (MCP protocol compatible).
                      If False, log to stdout only (standalone mode).
            bandit_config: Path to bandit config file (overrides config)
            skip_tests: List of test IDs to skip (overrides config)
            exclude_paths: Additional paths to exclude (overrides config)
            critical_threshold: Number of high severity issues to trigger CRITICAL status (overrides config)
            warning_threshold: Number of medium severity issues to trigger WARNING status (overrides config)
        """
        self.repo_path = repo_path or Path.cwd()
        input_dir, output_dir = self._init_directories(input_dir, output_dir, name, self.repo_path)

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.mcp_mode = mcp_mode
        self.logger = self._init_logger(name, mcp_mode)

        # Load config
        config = self._load_config(config_file)
        self.config = config or {}

        # Load from config file or defaultconfig.toml
        full_config = get_subserver_config("security", start_dir=str(self.repo_path))

        # Load reviewer mindset
        self.mindset = get_mindset(SECURITY_MINDSET, full_config)

        # Apply overrides
        self.severity_threshold, self.confidence_threshold = self._apply_threshold_overrides(severity_threshold, confidence_threshold, config)
        self.bandit_config, self.skip_tests, self.exclude_paths = self._apply_bandit_overrides(bandit_config, skip_tests, exclude_paths, full_config)
        self.critical_threshold, self.warning_threshold = self._apply_mindset_overrides(critical_threshold, warning_threshold, full_config)

    def _load_config(self, config_file: Path | None) -> dict | None:
        """Load configuration from file."""
        if config_file and config_file.exists():
            try:
                with open(config_file) as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get("security", {}) if full_config else {}
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                return None

        default_config = self.repo_path / ".glintefy.yaml"
        if default_config.exists():
            try:
                with open(default_config) as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get("security", {}) if full_config else {}
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                return None

        return None

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for security analysis."""
        missing = []

        # Check for files to analyze
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(f"No files list found in {self.input_dir}. Run scope sub-server first.")

        # Validate thresholds
        if self.severity_threshold not in self.SEVERITY_LEVELS:
            missing.append(f"Invalid severity_threshold: {self.severity_threshold}. Must be 'low', 'medium', or 'high'")
        if self.confidence_threshold not in self.SEVERITY_LEVELS:
            missing.append(f"Invalid confidence_threshold: {self.confidence_threshold}. Must be 'low', 'medium', or 'high'")

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute security analysis."""
        log_section(self.logger, "SECURITY ANALYSIS")

        try:
            # Step 1: Get files to analyze
            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()

            if not python_files:
                log_result(self.logger, True, "No Python files to analyze")
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Security Analysis\n\nNo Python files to analyze.",
                    artifacts={},
                    metrics={"files_scanned": 0, "issues_found": 0},
                )

            log_file_list(self.logger, python_files, "Python files", max_display=10)

            # Step 2: Run Bandit analysis
            log_step(self.logger, 2, "Running Bandit security scan")
            with LogContext(self.logger, "Bandit analysis"):
                bandit_results = self._run_bandit(python_files)

            # Step 3: Filter by threshold
            log_step(self.logger, 3, "Filtering results by threshold")
            filtered_issues = self._filter_issues(bandit_results)

            # Step 4: Categorize by severity
            log_step(self.logger, 4, "Categorizing issues")
            categorized = self._categorize_issues(filtered_issues)

            # Step 5: Save results
            log_step(self.logger, 5, "Saving results")
            artifacts = self._save_results(bandit_results, filtered_issues)

            # Step 6: Generate summary
            summary = self._generate_summary(python_files, filtered_issues, categorized)

            # Determine status based on thresholds (use categorized for efficiency)
            high_count = len(categorized.get("HIGH", []))
            medium_count = len(categorized.get("MEDIUM", []))

            if high_count >= self.critical_threshold:
                status = "PARTIAL"  # CRITICAL - too many high severity issues
            elif medium_count >= self.warning_threshold:
                status = "PARTIAL"  # WARNING - too many medium severity issues
            else:
                status = "SUCCESS"

            log_result(
                self.logger,
                status == "SUCCESS",
                f"Scan complete: {len(filtered_issues)} issues found",
            )

            metrics = SecurityMetrics(
                files_scanned=len(python_files),
                issues_found=len(filtered_issues),
                high_severity=high_count,
                medium_severity=medium_count,
                low_severity=len(categorized.get("LOW", [])),
            )

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=metrics.model_dump(),
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
                summary=f"# Security Analysis Failed\n\n**Error**: {e}",
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

        # Convert to absolute paths
        return [str(self.repo_path / f) for f in python_files]

    def _filter_existing_files(self, files: list[str]) -> list[str]:
        """Filter to only existing files."""
        return [f for f in files if Path(f).exists()]

    def _apply_exclude_patterns(self, files: list[str]) -> list[str]:
        """Apply exclude path patterns to file list."""
        if not self.exclude_paths:
            return files

        filtered_files = []
        for f in files:
            file_path = Path(f)
            excluded = any(file_path.match(pattern) for pattern in self.exclude_paths)
            if not excluded:
                filtered_files.append(f)
        return filtered_files

    def _build_bandit_command(self, files: list[str]) -> list[str]:
        """Build bandit command with config and skip options."""
        cmd = ["bandit", "-f", "json", "-r"]

        # Add config file if specified
        if self.bandit_config:
            config_path = Path(self.bandit_config)
            if config_path.exists():
                cmd.extend(["-c", str(config_path)])
            else:
                self.logger.warning(f"Bandit config file not found: {self.bandit_config}")

        # Add skip tests if specified
        if self.skip_tests:
            for test_id in self.skip_tests:
                cmd.extend(["-s", test_id])

        # Add files to scan
        cmd.extend(files)
        return cmd

    def _compute_relative_path(self, filename: str) -> str:
        """Compute relative path for a file."""
        try:
            return str(Path(filename).relative_to(self.repo_path))
        except ValueError:
            return filename

    def _run_bandit(self, files: list[str]) -> list[BanditIssue]:
        """Run Bandit security scanner on files."""
        existing_files = self._filter_existing_files(files)
        if not existing_files:
            return []

        filtered_files = self._apply_exclude_patterns(existing_files)
        if not filtered_files:
            return []

        try:
            cmd = self._build_bandit_command(filtered_files)
            bandit_timeout = get_timeout("tool_analysis", 120, start_dir=str(self.repo_path))
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=bandit_timeout)

            if result.stdout.strip():
                data = json.loads(result.stdout)
                raw_results = data.get("results", [])
                # Convert to typed BanditIssue at parse boundary
                issues = []
                for raw in raw_results:
                    # Add relative path before conversion
                    if "filename" in raw:
                        raw["relative_file"] = self._compute_relative_path(raw["filename"])
                    issues.append(BanditIssue.model_validate(raw))
                return issues

        except subprocess.TimeoutExpired:
            self.logger.warning("Bandit scan timed out")
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON from Bandit: {e}")
        except FileNotFoundError:
            self.logger.error("Bandit not found. Install with: pip install bandit")
        except Exception as e:
            self.logger.warning(f"Error running Bandit: {e}")

        return []

    def _filter_issues(self, issues: list[BanditIssue]) -> list[BanditIssue]:
        """Filter issues by severity and confidence thresholds."""
        severity_min = self.SEVERITY_LEVELS.get(self.severity_threshold, 1)
        confidence_min = self.SEVERITY_LEVELS.get(self.confidence_threshold, 1)

        filtered = []
        for issue in issues:
            issue_severity = self.SEVERITY_LEVELS.get(issue.issue_severity.lower(), 0)
            issue_confidence = self.SEVERITY_LEVELS.get(issue.issue_confidence.lower(), 0)

            if issue_severity >= severity_min and issue_confidence >= confidence_min:
                filtered.append(issue)

        return filtered

    def _categorize_issues(self, issues: list[BanditIssue]) -> dict[str, list[BanditIssue]]:
        """Categorize issues by severity."""
        categorized: dict[str, list[BanditIssue]] = {
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
        }

        for issue in issues:
            severity = issue.issue_severity.upper()
            if severity in categorized:
                categorized[severity].append(issue)
            else:
                categorized["LOW"].append(issue)

        return categorized

    def _save_results(
        self,
        all_results: list[BanditIssue],
        filtered_results: list[BanditIssue],
    ) -> dict[str, Path]:
        """Save analysis results to files."""
        artifacts = {}
        report_dir = self.output_dir.parent / "report"

        # Convert to dicts at serialization boundary
        all_dicts = [issue.model_dump() for issue in all_results]
        filtered_dicts = [issue.model_dump() for issue in filtered_results]

        # Save all results (unfiltered)
        all_file = self.output_dir / "bandit_full.json"
        all_file.write_text(json.dumps(all_dicts, indent=2))
        artifacts["bandit_full"] = all_file

        # Save filtered results
        filtered_file = self.output_dir / "security_issues.json"
        filtered_file.write_text(json.dumps(filtered_dicts, indent=2))
        artifacts["security_issues"] = filtered_file

        # Write chunked issues if any filtered results
        if filtered_results:
            # Get unique issue types before conversion (typed access)
            issue_types = list({issue.type for issue in filtered_results})

            # Cleanup old chunked files
            cleanup_chunked_issues(
                output_dir=report_dir,
                issue_types=issue_types,
                prefix="issues",
            )

            # Write chunked issues (use already-converted dicts)
            written_files = write_chunked_issues(
                issues=filtered_dicts,
                output_dir=report_dir,
                prefix="issues",
            )

            if written_files:
                artifacts["issues"] = written_files[0]

        return artifacts

    def _generate_summary(
        self,
        files: list[str],
        issues: list[BanditIssue],
        categorized: dict[str, list[BanditIssue]],
    ) -> str:
        """Generate markdown summary with mindset evaluation."""
        verdict = self._evaluate_mindset(files, categorized)

        lines = []
        lines.extend(self._format_security_header(verdict, files, issues, categorized))
        lines.extend(self._format_high_severity_issues(categorized))
        lines.extend(self._format_medium_severity_issues(categorized))
        lines.extend(self._format_recommendations(issues, categorized))
        lines.extend(self._format_approval_status(verdict))

        return "\n".join(lines)

    def _evaluate_mindset(self, files: list[str], categorized: dict[str, list[BanditIssue]]) -> Any:
        """Evaluate results using mindset."""
        high_issues = categorized.get("HIGH", [])
        medium_issues = categorized.get("MEDIUM", [])
        critical_issues = [{"severity": "critical"} for _ in high_issues]
        warning_issues = [{"severity": "warning"} for _ in medium_issues]

        return evaluate_results(
            self.mindset,
            critical_issues,
            warning_issues,
            max(len(files), 1),
        )

    def _format_security_header(
        self,
        verdict: Any,
        files: list[str],
        issues: list[BanditIssue],
        categorized: dict[str, list[BanditIssue]],
    ) -> list[str]:
        """Format security report header."""
        high_issues = categorized.get("HIGH", [])
        medium_issues = categorized.get("MEDIUM", [])

        return [
            "# Security Analysis Report",
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
            f"- High severity: {len(high_issues)}",
            f"- Medium severity: {len(medium_issues)}",
            f"- Files scanned: {len(files)}",
            "",
            "## Overview",
            "",
            f"**Files Scanned**: {len(files)}",
            f"**Issues Found**: {len(issues)}",
            "",
            "## Configuration",
            "",
            f"- Severity Threshold: {self.severity_threshold}",
            f"- Confidence Threshold: {self.confidence_threshold}",
            f"- Critical Status Threshold: {self.critical_threshold} high severity issues",
            f"- Warning Status Threshold: {self.warning_threshold} medium severity issues",
            "",
            "## Issues by Severity",
            "",
            f"- [HIGH] **High**: {len(categorized.get('HIGH', []))}",
            f"- [MED] **Medium**: {len(categorized.get('MEDIUM', []))}",
            f"- [LOW] **Low**: {len(categorized.get('LOW', []))}",
            "",
        ]

    def _format_high_severity_issues(self, categorized: dict[str, list[BanditIssue]]) -> list[str]:
        """Format high severity issues section."""
        high_issues = categorized.get("HIGH", [])
        if not high_issues:
            return []

        limit = get_display_limit("max_high_security", 10, start_dir=str(self.repo_path))
        display_count = len(high_issues) if limit is None else min(limit, len(high_issues))

        header = "## [HIGH] High Severity Issues" if limit is None else f"## [HIGH] High Severity Issues (showing {display_count} of {len(high_issues)})"
        lines = [header, ""]

        for issue in high_issues[:limit]:
            file_path = issue.relative_file or issue.filename or "unknown"
            line_num = issue.line_number or "?"
            test_id = issue.test_id
            message = issue.issue_text or "Unknown issue"
            lines.append(f"- **{file_path}:{line_num}** [{test_id}] {message}")

        if limit is not None and len(high_issues) > limit:
            lines.append("")
            lines.append(
                f"*Note: {len(high_issues) - limit} more high severity issues not shown. Set `output.display.max_high_security = 0` in config for unlimited display.*"
            )
        lines.append("")

        return lines

    def _format_medium_severity_issues(self, categorized: dict[str, list[BanditIssue]]) -> list[str]:
        """Format medium severity issues section."""
        medium_issues = categorized.get("MEDIUM", [])
        if not medium_issues:
            return []

        limit = get_display_limit("max_medium_security", 10, start_dir=str(self.repo_path))
        display_count = len(medium_issues) if limit is None else min(limit, len(medium_issues))

        header = "## [MED] Medium Severity Issues" if limit is None else f"## [MED] Medium Severity Issues (showing {display_count} of {len(medium_issues)})"
        lines = [header, ""]

        for issue in medium_issues[:limit]:
            file_path = issue.relative_file or issue.filename or "unknown"
            line_num = issue.line_number or "?"
            message = issue.issue_text or "Unknown issue"
            lines.append(f"- `{file_path}:{line_num}`: {message}")

        if limit is not None and len(medium_issues) > limit:
            lines.append("")
            lines.append(
                f"*Note: {len(medium_issues) - limit} more medium severity issues not shown. Set `output.display.max_medium_security = 0` in config for unlimited display.*"
            )
        lines.append("")

        return lines

    def _format_recommendations(self, issues: list[BanditIssue], categorized: dict[str, list[BanditIssue]]) -> list[str]:
        """Format recommendations section."""
        lines = ["## Recommendations", ""]

        high_issues = categorized.get("HIGH", [])
        medium_issues = categorized.get("MEDIUM", [])

        if high_issues:
            lines.append("1. **Fix high severity issues immediately** - These represent significant security risks")
        if medium_issues:
            lines.append("2. **Review medium severity issues** - Address before production deployment")
        if not issues:
            lines.append("[PASS] No security issues detected!")

        return lines

    def _format_approval_status(self, verdict: Any) -> list[str]:
        """Format approval status section."""
        lines = ["", "## Approval Status", "", f"**{verdict.verdict_text}**"]

        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")

        return lines
