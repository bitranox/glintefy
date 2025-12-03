"""Docs sub-server: Documentation coverage and quality analysis.

This sub-server analyzes documentation for:
- Docstring coverage (interrogate)
- Missing parameter documentation
- README/CHANGELOG validation
- Documentation accuracy
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from glintefy.config import get_config, get_display_limit, get_subserver_config, get_timeout
from glintefy.subservers.base import BaseSubServer, SubServerResult
from glintefy.subservers.common.chunked_writer import (
    cleanup_chunked_issues,
    write_chunked_issues,
)
from glintefy.subservers.common.issues import (
    BaseIssue,
    DocsMetrics,
    DocstringIssue,
)
from glintefy.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_error_detailed,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from glintefy.subservers.common.mindsets import (
    DOCS_MINDSET,
    evaluate_results,
    get_mindset,
)
from glintefy.subservers.review.docs_project import (
    ProjectDocsConfig,
    ProjectDocsResult,
    check_project_docs,
)
from glintefy.subservers.review.docs_style import validate_docstring_style
from glintefy.tools_venv import ensure_tools_venv, get_tool_path


class DocsSubServer(BaseSubServer):
    """Documentation coverage and quality analyzer.

    Analyzes documentation quality including:
    - Docstring coverage using interrogate
    - Missing parameter/return documentation
    - Project documentation (README, CHANGELOG)
    - Documentation accuracy validation
    """

    REQUIRED_PROJECT_DOCS = ["README.md", "README.rst", "README.txt"]
    OPTIONAL_PROJECT_DOCS = ["CHANGELOG.md", "CONTRIBUTING.md", "LICENSE"]

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

    def _apply_feature_overrides(self, check_docstrings: bool | None, check_project_docs: bool | None, config: dict) -> tuple[bool, bool]:
        """Apply feature flag overrides."""
        check_docs = check_docstrings if check_docstrings is not None else config.get("check_docstrings", True)
        check_proj = check_project_docs if check_project_docs is not None else config.get("check_project_docs", True)
        return check_docs, check_proj

    def _apply_threshold_overrides(self, min_coverage: int | None, docstring_style: str | None, config: dict) -> tuple[int, str]:
        """Apply threshold and style overrides."""
        coverage = min_coverage if min_coverage is not None else config.get("min_coverage", 80)
        style = docstring_style if docstring_style is not None else config.get("docstring_style", "google")
        return coverage, style

    def _apply_project_doc_overrides(
        self,
        require_readme: bool | None,
        require_changelog: bool | None,
        required_readme_sections: list[str] | None,
        config: dict,
    ) -> tuple[bool, bool, list[str]]:
        """Apply project documentation requirement overrides."""
        readme = require_readme if require_readme is not None else config.get("require_readme", True)
        changelog = require_changelog if require_changelog is not None else config.get("require_changelog", False)
        sections = required_readme_sections if required_readme_sections is not None else config.get("required_readme_sections", [])
        return readme, changelog, sections

    def __init__(
        self,
        name: str = "docs",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        check_docstrings: bool | None = None,
        check_project_docs: bool | None = None,
        min_coverage: int | None = None,
        docstring_style: str | None = None,
        mcp_mode: bool = False,
        require_readme: bool | None = None,
        require_changelog: bool | None = None,
        required_readme_sections: list[str] | None = None,
    ):
        """Initialize docs sub-server.

        Args:
            name: Sub-server name
            input_dir: Input directory (containing files_to_review.txt from scope)
            output_dir: Output directory for results
            repo_path: Repository path (default: current directory)
            check_docstrings: Whether to check docstring coverage
            check_project_docs: Whether to check project documentation files
            min_coverage: Minimum docstring coverage percentage
            docstring_style: Docstring style (google, numpy, sphinx)
            mcp_mode: If True, log to stderr only (MCP protocol compatible)
            require_readme: If True, missing README is critical (default: True)
            require_changelog: If True, report missing CHANGELOG (default: False)
            required_readme_sections: List of required README sections
        """
        self.repo_path = repo_path or Path.cwd()
        input_dir, output_dir = self._init_directories(input_dir, output_dir, name, self.repo_path)

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.mcp_mode = mcp_mode
        self.logger = self._init_logger(name, mcp_mode)

        # Load config
        config = get_subserver_config("docs", start_dir=str(self.repo_path))
        self.config = config

        # Load reviewer mindset
        self.mindset = get_mindset(DOCS_MINDSET, config)

        # Apply overrides
        self.check_docstrings, self.check_project_docs = self._apply_feature_overrides(check_docstrings, check_project_docs, config)
        self.min_coverage, self.docstring_style = self._apply_threshold_overrides(min_coverage, docstring_style, config)
        self.require_readme, self.require_changelog, self.required_readme_sections = self._apply_project_doc_overrides(
            require_readme, require_changelog, required_readme_sections, config
        )

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for documentation analysis."""
        missing = []

        # Check for files to analyze
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(f"No files list found in {self.input_dir}. Run scope sub-server first.")

        return len(missing) == 0, missing

    def _run_docstring_coverage_check(self, results: dict, all_issues: list) -> None:
        """Run docstring coverage analysis."""
        log_step(self.logger, 2, "Checking docstring coverage")
        with LogContext(self.logger, "Docstring coverage"):
            coverage = self._check_docstring_coverage()
            results["docstring_coverage"] = coverage
            if coverage.get("coverage_percent", 100) < self.min_coverage:
                all_issues.append(
                    DocstringIssue(
                        type="low_docstring_coverage",
                        severity="warning",
                        message=f"Docstring coverage is {coverage.get('coverage_percent', 0)}% (minimum: {self.min_coverage}%)",
                        doc_type="coverage",
                    )
                )

    def _run_missing_docstrings_check(self, python_files: list[str], results: dict, all_issues: list) -> None:
        """Find missing docstrings."""
        log_step(self.logger, 3, "Finding missing docstrings")
        with LogContext(self.logger, "Missing docstrings"):
            missing = self._find_missing_docstrings(python_files)
            results["missing_docstrings"] = missing
            all_issues.extend(missing)

    def _run_project_docs_check(self, results: dict, all_issues: list) -> None:
        """Check project documentation."""
        log_step(self.logger, 4, "Checking project documentation")
        with LogContext(self.logger, "Project docs"):
            project_docs = self._check_project_docs()
            results["project_docs"] = project_docs
            all_issues.extend(project_docs.issues)

    def _determine_status(self, all_issues: list[BaseIssue]) -> str:
        """Determine analysis status based on issues."""
        critical_count = len([i for i in all_issues if i.severity == "critical"])
        return "SUCCESS" if critical_count == 0 else "PARTIAL"

    def execute(self) -> SubServerResult:
        """Execute documentation analysis."""
        log_section(self.logger, "DOCUMENTATION ANALYSIS")

        try:
            log_step(self.logger, 0, "Ensuring tools venv")
            ensure_tools_venv()

            results: dict[str, Any] = {
                "docstring_coverage": {},
                "missing_docstrings": [],
                "project_docs": {},
                "doc_issues": [],
            }
            all_issues: list[BaseIssue] = []

            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()

            if self.check_docstrings and python_files:
                self._run_docstring_coverage_check(results, all_issues)
                self._run_missing_docstrings_check(python_files, results, all_issues)

            if self.check_project_docs:
                self._run_project_docs_check(results, all_issues)

            log_step(self.logger, 5, "Saving results")
            artifacts = self._save_results(results, all_issues)

            summary = self._generate_summary(results, all_issues, python_files)
            status = self._determine_status(all_issues)

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
                summary=f"# Documentation Analysis Failed\n\n**Error**: {e}",
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

    def _parse_coverage_percentage(self, line: str) -> float | None:
        """Extract coverage percentage from interrogate TOTAL line."""
        import re

        match = re.search(r"(\d+\.?\d*)%", line)
        if match:
            return float(match.group(1))
        return None

    def _parse_missing_count(self, line: str) -> int | None:
        """Extract missing count from interrogate output."""
        import re

        match = re.search(r"(\d+)", line)
        if match:
            return int(match.group(1))
        return None

    def _process_total_line(self, line: str, coverage: dict[str, Any]) -> None:
        """Process TOTAL line from interrogate output."""
        percentage = self._parse_coverage_percentage(line)
        if percentage is not None:
            coverage["coverage_percent"] = percentage

    def _process_missing_line(self, line: str, coverage: dict[str, Any]) -> None:
        """Process missing count line from interrogate output."""
        missing = self._parse_missing_count(line)
        if missing is not None:
            coverage["missing"] = missing

    def _parse_interrogate_output(self, output: str, coverage: dict[str, Any]) -> None:
        """Parse interrogate output to extract coverage metrics."""
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                self._process_total_line(line, coverage)
            elif "missing" in line.lower():
                self._process_missing_line(line, coverage)

        coverage["raw_output"] = output

    def _check_docstring_coverage(self) -> dict[str, Any]:
        """Check docstring coverage using interrogate."""
        coverage = {"coverage_percent": 0, "missing": 0, "total": 0}

        try:
            python_path = get_tool_path("python")
            interrogate_timeout = get_timeout("tool_analysis", 120, start_dir=str(self.repo_path))
            result = subprocess.run(
                [str(python_path), "-m", "interrogate", "-v", str(self.repo_path / "src")],
                check=False,
                capture_output=True,
                text=True,
                timeout=interrogate_timeout,
            )
            self._parse_interrogate_output(result.stdout, coverage)

        except FileNotFoundError:
            self.logger.info("interrogate not available")
        except Exception as e:
            self.logger.warning(f"interrogate error: {e}")

        return coverage

    def _check_function_docstring(self, node, file_path: str, issues: list) -> None:
        """Check if a function has docstring and validate style."""
        import ast

        if node.name.startswith("_") and not node.name.startswith("__"):
            return  # Skip private functions

        docstring = ast.get_docstring(node)
        if not docstring:
            issues.append(
                DocstringIssue(
                    type="missing_docstring",
                    severity="warning",
                    file=file_path,
                    line=node.lineno,
                    name=node.name,
                    doc_type="function",
                    message=f"Function '{node.name}' is missing a docstring",
                )
            )
        else:
            style_issue = self._validate_docstring_style(docstring, node.name, file_path, node.lineno, "function")
            if style_issue:
                issues.append(style_issue)

    def _check_class_docstring(self, node, file_path: str, issues: list) -> None:
        """Check if a class has docstring and validate style."""
        import ast

        docstring = ast.get_docstring(node)
        if not docstring:
            issues.append(
                DocstringIssue(
                    type="missing_docstring",
                    severity="warning",
                    file=file_path,
                    line=node.lineno,
                    name=node.name,
                    doc_type="class",
                    message=f"Class '{node.name}' is missing a docstring",
                )
            )
        else:
            style_issue = self._validate_docstring_style(docstring, node.name, file_path, node.lineno, "class")
            if style_issue:
                issues.append(style_issue)

    def _process_ast_node(self, node: object, file_path: str, issues: list[DocstringIssue]) -> None:
        """Process a single AST node for docstring checks."""
        import ast

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._check_function_docstring(node, file_path, issues)
        elif isinstance(node, ast.ClassDef):
            self._check_class_docstring(node, file_path, issues)

    def _analyze_file_for_docstrings(self, file_path: str) -> list[DocstringIssue]:
        """Analyze a single file for missing docstrings."""
        import ast

        issues: list[DocstringIssue] = []
        try:
            content = Path(file_path).read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                self._process_ast_node(node, file_path, issues)

        except SyntaxError:
            self.logger.warning(f"Syntax error in {file_path}")
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")

        return issues

    def _find_missing_docstrings(self, files: list[str]) -> list[DocstringIssue]:
        """Find functions/classes without docstrings."""
        issues: list[DocstringIssue] = []
        for file_path in files:
            issues.extend(self._analyze_file_for_docstrings(file_path))
        return issues

    def _validate_docstring_style(
        self,
        docstring: str,
        name: str,
        file_path: str,
        line: int,
        doc_type: str,
    ) -> DocstringIssue | None:
        """Validate docstring conforms to configured style.

        Delegates to docs_style module for cleaner separation.
        Returns DocstringIssue directly, no conversion needed.
        """
        return validate_docstring_style(
            docstring=docstring,
            name=name,
            file_path=file_path,
            line=line,
            doc_type=doc_type,
            expected_style=self.docstring_style,
        )

    def _check_project_docs(self) -> ProjectDocsResult:
        """Check project documentation files.

        Delegates to docs_project module for cleaner separation.
        """
        config = ProjectDocsConfig(
            require_readme=self.require_readme,
            require_changelog=self.require_changelog,
            required_readme_sections=self.required_readme_sections,
        )
        return check_project_docs(self.repo_path, config, self.logger)

    def _save_docstring_coverage(self, results: dict[str, Any], artifacts: dict) -> None:
        """Save docstring coverage results."""
        if not results.get("docstring_coverage"):
            return
        path = self.output_dir / "docstring_coverage.json"
        coverage_data = {k: v for k, v in results["docstring_coverage"].items() if k != "raw_output"}
        path.write_text(json.dumps(coverage_data, indent=2))
        artifacts["docstring_coverage"] = path

    def _save_missing_docstrings(self, results: dict[str, Any], artifacts: dict) -> None:
        """Save missing docstrings results.

        Converts DocstringIssue dataclasses to dicts at serialization boundary.
        """
        missing_docstrings: list[DocstringIssue] = results.get("missing_docstrings", [])
        if not missing_docstrings:
            return
        path = self.output_dir / "missing_docstrings.json"
        # Convert dataclasses to dicts at serialization boundary
        missing_dicts = [issue.to_dict() for issue in missing_docstrings]
        path.write_text(json.dumps(missing_dicts, indent=2))
        artifacts["missing_docstrings"] = path

    def _save_project_docs(self, results: dict[str, Any], artifacts: dict) -> None:
        """Save project documentation results.

        Converts ProjectDocsResult dataclass to dict at serialization boundary.
        """
        project_docs: ProjectDocsResult | None = results.get("project_docs")
        if not project_docs:
            return
        path = self.output_dir / "project_docs.json"
        # Convert dataclass to dict at serialization boundary
        doc_data = {
            "readme": project_docs.readme,
            "readme_path": project_docs.readme_path,
            "changelog": project_docs.changelog,
            "contributing": project_docs.contributing,
            "license": project_docs.license,
            "issues": [issue.to_dict() for issue in project_docs.issues],
        }
        path.write_text(json.dumps(doc_data, indent=2))
        artifacts["project_docs"] = path

    def _save_chunked_issues(self, all_issues: list[BaseIssue], artifacts: dict) -> None:
        """Save chunked issues to report directory."""
        if not all_issues:
            return

        report_dir = self.output_dir.parent / "report"
        # Extract issue types before conversion (typed access)
        issue_types = list({issue.type for issue in all_issues})
        issues_dicts = [i.to_dict() for i in all_issues]

        cleanup_chunked_issues(output_dir=report_dir, issue_types=issue_types, prefix="issues")
        written_files = write_chunked_issues(issues=issues_dicts, output_dir=report_dir, prefix="issues")

        if written_files:
            artifacts["issues"] = written_files[0]

    def _save_results(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Path]:
        """Save all results to files."""
        artifacts = {}
        self._save_docstring_coverage(results, artifacts)
        self._save_missing_docstrings(results, artifacts)
        self._save_project_docs(results, artifacts)
        self._save_chunked_issues(all_issues, artifacts)
        return artifacts

    def _compile_metrics(self, files: list[str], results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Any]:
        """Compile metrics for result."""
        project_docs: ProjectDocsResult | None = results.get("project_docs")
        project_docs_found = 0
        if project_docs:
            project_docs_found = sum([project_docs.readme, project_docs.changelog, project_docs.license])
        return DocsMetrics(
            files_analyzed=len(files),
            coverage_percent=results.get("docstring_coverage", {}).get("coverage_percent", 0),
            missing_docstrings=len(results.get("missing_docstrings", [])),
            project_docs_found=project_docs_found,
            total_issues=len(all_issues),
        ).model_dump()

    def _format_docstring_item(self, item: DocstringIssue) -> str:
        """Format a single docstring item."""
        return f"- `{item.file}:{item.line}` - {item.doc_type} `{item.name}`"

    def _format_missing_docstrings_section(self, missing: list[DocstringIssue]) -> list[str]:
        """Format missing docstrings section."""
        if not missing:
            return []

        limit = get_display_limit("max_missing_docstrings", 15, start_dir=str(self.repo_path))
        display_count = len(missing) if limit is None else min(limit, len(missing))
        header = "## Missing Docstrings" if limit is None else f"## Missing Docstrings (showing {display_count} of {len(missing)})"

        lines = [header, ""]
        for item in missing[:limit]:
            lines.append(self._format_docstring_item(item))

        if limit is not None and len(missing) > limit:
            lines.append("")
            lines.append(
                f"*Note: {len(missing) - limit} more missing docstrings not shown. Set `output.display.max_missing_docstrings = 0` in config for unlimited display.*"
            )
        lines.append("")
        return lines

    def _format_header_section(self, verdict, files_count: int) -> list[str]:
        """Format report header with mindset and verdict."""
        return [
            "# Documentation Analysis Report",
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
            f"- Files analyzed: {files_count}",
            "",
        ]

    def _format_overview_section(self, metrics: dict, doc_cov: dict, project_docs: ProjectDocsResult | None) -> list[str]:
        """Format overview and project documentation sections."""
        lines = [
            "## Overview",
            "",
            f"**Files Analyzed**: {metrics['files_analyzed']}",
            f"**Docstring Coverage**: {doc_cov.get('coverage_percent', 0)}% (minimum: {self.min_coverage}%)",
            f"**Missing Docstrings**: {metrics['missing_docstrings']}",
            f"**Total Issues**: {metrics['total_issues']}",
            "",
            "## Project Documentation",
            "",
        ]
        if project_docs:
            lines.extend(
                [
                    f"- README: {'[PASS]' if project_docs.readme else '[FAIL]'}",
                    f"- CHANGELOG: {'[PASS]' if project_docs.changelog else '[WARN]'}",
                    f"- CONTRIBUTING: {'[PASS]' if project_docs.contributing else '[WARN]'}",
                    f"- LICENSE: {'[PASS]' if project_docs.license else '[FAIL]'}",
                    "",
                ]
            )
        else:
            lines.extend(["*Project documentation check not run*", ""])
        return lines

    def _format_approval_section(self, verdict) -> list[str]:
        """Format approval status section."""
        lines = ["## Approval Status", "", f"**{verdict.verdict_text}**"]
        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")
        return lines

    def _generate_summary(self, results: dict[str, Any], all_issues: list[BaseIssue], files: list[str]) -> str:
        """Generate markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(files, results, all_issues)
        doc_cov = results.get("docstring_coverage", {})
        project_docs: ProjectDocsResult | None = results.get("project_docs")

        critical_issues = [i for i in all_issues if i.severity == "critical"]
        warning_issues = [i for i in all_issues if i.severity == "warning"]
        verdict = evaluate_results(self.mindset, critical_issues, warning_issues, max(len(files), 1))

        lines = []
        lines.extend(self._format_header_section(verdict, len(files)))
        lines.extend(self._format_overview_section(metrics, doc_cov, project_docs))
        lines.extend(self._format_missing_docstrings_section(results.get("missing_docstrings", [])))
        lines.extend(self._format_approval_section(verdict))

        return "\n".join(lines)
