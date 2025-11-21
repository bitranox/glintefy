"""Quality sub-server: Analyze code quality metrics.

This sub-server analyzes code quality using:
- Cyclomatic complexity (radon)
- Maintainability index
- Lines of code metrics
- Code smell detection
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.logging import (
    LogContext,
    log_dict,
    log_file_list,
    log_metric,
    log_result,
    log_section,
    log_step,
    setup_logger,
)


class QualitySubServer(BaseSubServer):
    """Analyze code quality metrics.

    Runs quality analysis tools and reports on:
    - Cyclomatic complexity per function
    - Maintainability index per file
    - High complexity warnings
    - Code metrics summary

    Args:
        name: Sub-server name (default: "quality")
        input_dir: Input directory (containing files_to_review.txt from scope)
        output_dir: Output directory for results
        repo_path: Repository path (default: current directory)
        complexity_threshold: Complexity threshold for warnings (default: 10)
        maintainability_threshold: MI threshold for warnings (default: 20)
        config_file: Path to config file

    Example:
        >>> server = QualitySubServer(
        ...     input_dir=Path("LLM-CONTEXT/review-anal/scope"),
        ...     output_dir=Path("LLM-CONTEXT/review-anal/quality"),
        ...     complexity_threshold=10
        ... )
        >>> result = server.run()
    """

    def __init__(
        self,
        name: str = "quality",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        complexity_threshold: int = 10,
        maintainability_threshold: int = 20,
        config_file: Path | None = None,
    ):
        """Initialize quality sub-server."""
        if input_dir is None:
            input_dir = Path.cwd() / "LLM-CONTEXT" / "review-anal" / "scope"
        if output_dir is None:
            output_dir = Path.cwd() / "LLM-CONTEXT" / "review-anal" / name

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()

        # Initialize logger
        self.logger = setup_logger(
            name, log_file=self.output_dir / f"{name}.log", level=20
        )

        # Load config
        config = self._load_config(config_file)

        # Apply config with parameter priority
        self.complexity_threshold = (
            complexity_threshold
            if complexity_threshold != 10 or config is None
            else config.get("complexity_threshold", 10)
        )
        self.maintainability_threshold = (
            maintainability_threshold
            if maintainability_threshold != 20 or config is None
            else config.get("maintainability_threshold", 20)
        )

    def _load_config(self, config_file: Path | None) -> dict | None:
        """Load configuration from file."""
        if config_file and config_file.exists():
            try:
                with open(config_file) as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get("quality", {}) if full_config else {}
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                return None

        default_config = self.repo_path / ".btx-review.yaml"
        if default_config.exists():
            try:
                with open(default_config) as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get("quality", {}) if full_config else {}
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                return None

        return None

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for quality analysis."""
        missing = []

        # Check for files to analyze
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            # Also check for files_code.txt
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(
                    f"No files list found in {self.input_dir}. "
                    "Run scope sub-server first."
                )

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute quality analysis."""
        log_section(self.logger, "QUALITY ANALYSIS")

        try:
            # Step 1: Get files to analyze
            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()

            if not python_files:
                log_result(self.logger, True, "No Python files to analyze")
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Quality Analysis\n\nNo Python files to analyze.",
                    artifacts={},
                    metrics={"files_analyzed": 0},
                )

            log_file_list(self.logger, python_files, "Python files", max_display=10)

            # Step 2: Run complexity analysis
            log_step(self.logger, 2, "Analyzing cyclomatic complexity")
            with LogContext(self.logger, "Complexity analysis"):
                complexity_results = self._analyze_complexity(python_files)

            # Step 3: Run maintainability analysis
            log_step(self.logger, 3, "Analyzing maintainability index")
            with LogContext(self.logger, "Maintainability analysis"):
                mi_results = self._analyze_maintainability(python_files)

            # Step 4: Identify issues
            log_step(self.logger, 4, "Identifying quality issues")
            issues = self._identify_issues(complexity_results, mi_results)

            # Step 5: Save results
            log_step(self.logger, 5, "Saving results")
            artifacts = self._save_results(complexity_results, mi_results, issues)

            # Step 6: Generate summary
            summary = self._generate_summary(
                python_files, complexity_results, mi_results, issues
            )

            # Determine status
            status = "SUCCESS" if not issues else "PARTIAL"
            log_result(
                self.logger,
                status == "SUCCESS",
                f"Analysis complete: {len(issues)} issues found",
            )

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics={
                    "files_analyzed": len(python_files),
                    "total_functions": len(complexity_results),
                    "high_complexity_count": len(
                        [r for r in complexity_results if r.get("complexity", 0) > self.complexity_threshold]
                    ),
                    "low_mi_count": len(
                        [r for r in mi_results if r.get("mi", 100) < self.maintainability_threshold]
                    ),
                    "issues_count": len(issues),
                },
            )

        except Exception as e:
            self.logger.error(f"Quality analysis failed: {e}", exc_info=True)
            return SubServerResult(
                status="FAILED",
                summary=f"# Quality Analysis Failed\n\n**Error**: {e}",
                artifacts={},
                errors=[str(e)],
            )

    def _get_python_files(self) -> list[str]:
        """Get Python files to analyze."""
        # Try files_code.txt first (Python files from scope)
        files_list = self.input_dir / "files_code.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_to_review.txt"

        if not files_list.exists():
            return []

        all_files = files_list.read_text().strip().split("\n")
        python_files = [f for f in all_files if f.endswith(".py") and f]

        # Convert to absolute paths
        return [str(self.repo_path / f) for f in python_files]

    def _analyze_complexity(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze cyclomatic complexity using radon."""
        results = []

        for file_path in files:
            if not Path(file_path).exists():
                continue

            try:
                # Run radon cc (cyclomatic complexity)
                result = subprocess.run(
                    ["radon", "cc", "-j", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, functions in data.items():
                        for func in functions:
                            results.append({
                                "file": str(Path(filepath).relative_to(self.repo_path)),
                                "name": func.get("name", "unknown"),
                                "type": func.get("type", "function"),
                                "complexity": func.get("complexity", 0),
                                "rank": func.get("rank", "A"),
                                "lineno": func.get("lineno", 0),
                            })
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout analyzing {file_path}")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from radon for {file_path}")
            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        return results

    def _analyze_maintainability(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze maintainability index using radon."""
        results = []

        for file_path in files:
            if not Path(file_path).exists():
                continue

            try:
                # Run radon mi (maintainability index)
                result = subprocess.run(
                    ["radon", "mi", "-j", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, mi_data in data.items():
                        results.append({
                            "file": str(Path(filepath).relative_to(self.repo_path)),
                            "mi": mi_data.get("mi", 0),
                            "rank": mi_data.get("rank", "A"),
                        })
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout analyzing {file_path}")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from radon for {file_path}")
            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        return results

    def _identify_issues(
        self,
        complexity_results: list[dict],
        mi_results: list[dict],
    ) -> list[dict[str, Any]]:
        """Identify quality issues based on thresholds."""
        issues = []

        # High complexity issues
        for result in complexity_results:
            if result.get("complexity", 0) > self.complexity_threshold:
                issues.append({
                    "type": "high_complexity",
                    "severity": "warning" if result["complexity"] <= 20 else "error",
                    "file": result["file"],
                    "line": result.get("lineno", 0),
                    "name": result["name"],
                    "value": result["complexity"],
                    "threshold": self.complexity_threshold,
                    "message": f"Function '{result['name']}' has complexity {result['complexity']} (threshold: {self.complexity_threshold})",
                })

        # Low maintainability issues
        for result in mi_results:
            if result.get("mi", 100) < self.maintainability_threshold:
                issues.append({
                    "type": "low_maintainability",
                    "severity": "warning" if result["mi"] >= 10 else "error",
                    "file": result["file"],
                    "value": result["mi"],
                    "threshold": self.maintainability_threshold,
                    "message": f"File has maintainability index {result['mi']:.1f} (threshold: {self.maintainability_threshold})",
                })

        return issues

    def _save_results(
        self,
        complexity_results: list[dict],
        mi_results: list[dict],
        issues: list[dict],
    ) -> dict[str, Path]:
        """Save analysis results to files."""
        artifacts = {}

        # Save complexity results
        complexity_file = self.output_dir / "complexity.json"
        complexity_file.write_text(json.dumps(complexity_results, indent=2))
        artifacts["complexity"] = complexity_file

        # Save maintainability results
        mi_file = self.output_dir / "maintainability.json"
        mi_file.write_text(json.dumps(mi_results, indent=2))
        artifacts["maintainability"] = mi_file

        # Save issues
        if issues:
            issues_file = self.output_dir / "issues.json"
            issues_file.write_text(json.dumps(issues, indent=2))
            artifacts["issues"] = issues_file

        return artifacts

    def _generate_summary(
        self,
        files: list[str],
        complexity_results: list[dict],
        mi_results: list[dict],
        issues: list[dict],
    ) -> str:
        """Generate markdown summary."""
        high_complexity = [
            r for r in complexity_results
            if r.get("complexity", 0) > self.complexity_threshold
        ]
        low_mi = [
            r for r in mi_results
            if r.get("mi", 100) < self.maintainability_threshold
        ]

        lines = [
            "# Quality Analysis Report",
            "",
            "## Overview",
            "",
            f"**Files Analyzed**: {len(files)}",
            f"**Functions Analyzed**: {len(complexity_results)}",
            f"**Issues Found**: {len(issues)}",
            "",
            "## Configuration",
            "",
            f"- Complexity Threshold: {self.complexity_threshold}",
            f"- Maintainability Threshold: {self.maintainability_threshold}",
            "",
        ]

        # Complexity summary
        if complexity_results:
            avg_complexity = sum(r.get("complexity", 0) for r in complexity_results) / len(complexity_results)
            max_complexity = max(r.get("complexity", 0) for r in complexity_results)
            lines.extend([
                "## Complexity Metrics",
                "",
                f"- Average Complexity: {avg_complexity:.1f}",
                f"- Max Complexity: {max_complexity}",
                f"- High Complexity Functions: {len(high_complexity)}",
                "",
            ])

        # Maintainability summary
        if mi_results:
            avg_mi = sum(r.get("mi", 0) for r in mi_results) / len(mi_results)
            min_mi = min(r.get("mi", 100) for r in mi_results)
            lines.extend([
                "## Maintainability Metrics",
                "",
                f"- Average MI: {avg_mi:.1f}",
                f"- Lowest MI: {min_mi:.1f}",
                f"- Low MI Files: {len(low_mi)}",
                "",
            ])

        # Issues list
        if issues:
            lines.extend([
                "## Issues",
                "",
            ])
            for issue in issues[:20]:  # Limit to 20
                severity_icon = "🔴" if issue["severity"] == "error" else "🟡"
                lines.append(f"- {severity_icon} `{issue['file']}`: {issue['message']}")

            if len(issues) > 20:
                lines.append(f"- ... and {len(issues) - 20} more issues")
            lines.append("")

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])
        if high_complexity:
            lines.append("1. **Refactor complex functions** - Break down functions with high cyclomatic complexity")
        if low_mi:
            lines.append("2. **Improve maintainability** - Add documentation and simplify complex modules")
        if not issues:
            lines.append("✅ No quality issues detected!")

        return "\n".join(lines)
