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

from btx_fix_mcp.config import get_config, get_subserver_config
from btx_fix_mcp.subservers.common.issues import (
    BaseIssue,
    DocsMetrics,
    DocstringIssue,
    ProjectDocIssue,
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
    DOCS_MINDSET,
    evaluate_results,
    get_mindset,
)
from btx_fix_mcp.tools_venv import ensure_tools_venv, get_tool_path


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
    ):
        """Initialize docs sub-server."""
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
        config = get_subserver_config("docs", start_dir=str(self.repo_path))
        self.config = config

        # Load reviewer mindset
        self.mindset = get_mindset(DOCS_MINDSET, config)

        # Feature flags
        self.check_docstrings = check_docstrings if check_docstrings is not None else config.get("check_docstrings", True)
        self.check_project_docs = check_project_docs if check_project_docs is not None else config.get("check_project_docs", True)

        # Thresholds
        self.min_coverage = min_coverage if min_coverage is not None else config.get("min_coverage", 80)
        self.docstring_style = docstring_style if docstring_style is not None else config.get("docstring_style", "google")

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

    def execute(self) -> SubServerResult:
        """Execute documentation analysis."""
        log_section(self.logger, "DOCUMENTATION ANALYSIS")

        try:
            # Ensure tools venv
            log_step(self.logger, 0, "Ensuring tools venv")
            ensure_tools_venv()

            results: dict[str, Any] = {
                "docstring_coverage": {},
                "missing_docstrings": [],
                "project_docs": {},
                "doc_issues": [],
            }
            all_issues: list[BaseIssue] = []

            # Step 1: Get files to analyze
            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()

            # Step 2: Run interrogate for docstring coverage
            if self.check_docstrings and python_files:
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

            # Step 3: Find missing docstrings
            if self.check_docstrings and python_files:
                log_step(self.logger, 3, "Finding missing docstrings")
                with LogContext(self.logger, "Missing docstrings"):
                    missing = self._find_missing_docstrings(python_files)
                    results["missing_docstrings"] = missing
                    all_issues.extend(missing)

            # Step 4: Check project documentation
            if self.check_project_docs:
                log_step(self.logger, 4, "Checking project documentation")
                with LogContext(self.logger, "Project docs"):
                    project_docs = self._check_project_docs()
                    results["project_docs"] = project_docs
                    all_issues.extend(project_docs.get("issues", []))

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

    def _check_docstring_coverage(self) -> dict[str, Any]:
        """Check docstring coverage using interrogate."""
        coverage = {"coverage_percent": 0, "missing": 0, "total": 0}

        try:
            python_path = get_tool_path("python")
            result = subprocess.run(
                [str(python_path), "-m", "interrogate", "-v", str(self.repo_path / "src")],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse interrogate output
            for line in result.stdout.split("\n"):
                if "TOTAL" in line and "%" in line:
                    # Extract percentage
                    import re

                    match = re.search(r"(\d+\.?\d*)%", line)
                    if match:
                        coverage["coverage_percent"] = float(match.group(1))
                elif "missing" in line.lower():
                    match = re.search(r"(\d+)", line)
                    if match:
                        coverage["missing"] = int(match.group(1))

            coverage["raw_output"] = result.stdout

        except FileNotFoundError:
            self.logger.info("interrogate not available")
        except Exception as e:
            self.logger.warning(f"interrogate error: {e}")

        return coverage

    def _find_missing_docstrings(self, files: list[str]) -> list[DocstringIssue]:
        """Find functions/classes without docstrings."""
        import ast

        issues: list[DocstringIssue] = []

        for file_path in files:
            try:
                content = Path(file_path).read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip private functions
                        if node.name.startswith("_") and not node.name.startswith("__"):
                            continue
                        # Check for docstring
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

                    elif isinstance(node, ast.ClassDef):
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

            except SyntaxError:
                self.logger.warning(f"Syntax error in {file_path}")
            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        return issues

    def _check_project_docs(self) -> dict[str, Any]:
        """Check project documentation files."""
        issues: list[ProjectDocIssue] = []
        result: dict[str, Any] = {
            "readme": False,
            "changelog": False,
            "contributing": False,
            "license": False,
            "issues": issues,
        }

        # Check README
        readme_found = False
        for readme in self.REQUIRED_PROJECT_DOCS:
            if (self.repo_path / readme).exists():
                readme_found = True
                result["readme"] = True
                break

        if not readme_found:
            issues.append(
                ProjectDocIssue(
                    type="missing_readme",
                    severity="critical",
                    message="No README file found (README.md, README.rst, or README.txt)",
                    doc_file="README",
                    required=True,
                )
            )

        # Check optional docs
        if (self.repo_path / "CHANGELOG.md").exists():
            result["changelog"] = True
        if (self.repo_path / "CONTRIBUTING.md").exists():
            result["contributing"] = True
        if (self.repo_path / "LICENSE").exists() or (self.repo_path / "LICENSE.md").exists():
            result["license"] = True
        else:
            issues.append(
                ProjectDocIssue(
                    type="missing_license",
                    severity="warning",
                    message="No LICENSE file found",
                    doc_file="LICENSE",
                    required=False,
                )
            )

        return result

    def _save_results(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Path]:
        """Save all results to files."""
        artifacts = {}

        if results.get("docstring_coverage"):
            path = self.output_dir / "docstring_coverage.json"
            # Remove raw_output for JSON serialization
            coverage_data = {k: v for k, v in results["docstring_coverage"].items() if k != "raw_output"}
            path.write_text(json.dumps(coverage_data, indent=2))
            artifacts["docstring_coverage"] = path

        missing_docstrings = results.get("missing_docstrings", [])
        if missing_docstrings:
            path = self.output_dir / "missing_docstrings.json"
            # Convert dataclasses to dicts
            missing_dicts = [i.to_dict() if hasattr(i, "to_dict") else i for i in missing_docstrings]
            path.write_text(json.dumps(missing_dicts, indent=2))
            artifacts["missing_docstrings"] = path

        project_docs = results.get("project_docs", {})
        if project_docs:
            path = self.output_dir / "project_docs.json"
            # Convert issues in project_docs to dicts
            doc_data = dict(project_docs)
            doc_data["issues"] = [i.to_dict() if hasattr(i, "to_dict") else i for i in project_docs.get("issues", [])]
            path.write_text(json.dumps(doc_data, indent=2))
            artifacts["project_docs"] = path

        if all_issues:
            path = self.output_dir / "issues.json"
            issues_dicts = [i.to_dict() for i in all_issues]
            path.write_text(json.dumps(issues_dicts, indent=2))
            artifacts["issues"] = path

        return artifacts

    def _compile_metrics(self, files: list[str], results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Any]:
        """Compile metrics for result."""
        return DocsMetrics(
            files_analyzed=len(files),
            coverage_percent=results.get("docstring_coverage", {}).get("coverage_percent", 0),
            missing_docstrings=len(results.get("missing_docstrings", [])),
            project_docs_found=sum(1 for k in ["readme", "changelog", "license"] if results.get("project_docs", {}).get(k, False)),
            total_issues=len(all_issues),
        ).to_dict()

    def _generate_summary(self, results: dict[str, Any], all_issues: list[BaseIssue], files: list[str]) -> str:
        """Generate markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(files, results, all_issues)
        doc_cov = results.get("docstring_coverage", {})
        project_docs = results.get("project_docs", {})

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
            f"- Files analyzed: {len(files)}",
            "",
            "## Overview",
            "",
            f"**Files Analyzed**: {metrics['files_analyzed']}",
            f"**Docstring Coverage**: {doc_cov.get('coverage_percent', 0)}% (minimum: {self.min_coverage}%)",
            f"**Missing Docstrings**: {metrics['missing_docstrings']}",
            f"**Total Issues**: {metrics['total_issues']}",
            "",
            "## Project Documentation",
            "",
            f"- README: {'✅' if project_docs.get('readme') else '❌'}",
            f"- CHANGELOG: {'✅' if project_docs.get('changelog') else '⚠️'}",
            f"- CONTRIBUTING: {'✅' if project_docs.get('contributing') else '⚠️'}",
            f"- LICENSE: {'✅' if project_docs.get('license') else '❌'}",
            "",
        ]

        # Missing docstrings
        missing = results.get("missing_docstrings", [])
        if missing:
            lines.extend(["## Missing Docstrings", ""])
            for item in missing[:15]:
                file_path = item.file if hasattr(item, "file") else item.get("file", "")
                line_num = item.line if hasattr(item, "line") else item.get("line", 0)
                doc_type = item.doc_type if hasattr(item, "doc_type") else item.get("kind", "")
                name = item.name if hasattr(item, "name") else item.get("name", "")
                lines.append(f"- `{file_path}:{line_num}` - {doc_type} `{name}`")
            if len(missing) > 15:
                lines.append(f"- ... and {len(missing) - 15} more")
            lines.append("")

        # Approval status
        lines.extend(["## Approval Status", ""])
        lines.append(f"**{verdict.verdict_text}**")
        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)
