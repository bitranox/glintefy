"""Deps sub-server: Dependency vulnerability and compliance analysis.

This sub-server analyzes project dependencies for:
- Security vulnerabilities (CVEs) using pip-audit
- Outdated packages
- License compliance
- Dependency tree analysis
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
    DependencyTree,
    DepsMetrics,
    LicenseIssue,
    OutdatedIssue,
    VulnerabilityIssue,
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
    DEPS_MINDSET,
    evaluate_results,
    get_mindset,
)
from glintefy.subservers.review.deps_scanners import (
    OutdatedPackage,
    Vulnerability,
    check_outdated_packages,
    scan_vulnerabilities,
)
from glintefy.tools_venv import ensure_tools_venv, get_tool_path


class DepsSubServer(BaseSubServer):
    """Dependency vulnerability and compliance analyzer.

    Scans project dependencies for security vulnerabilities, outdated packages,
    and license compliance issues.

    Args:
        name: Sub-server name (default: "deps")
        output_dir: Output directory for results
        repo_path: Repository path (default: current directory)
        scan_vulnerabilities: Enable vulnerability scanning
        check_licenses: Enable license compliance checking
        check_outdated: Enable outdated package detection
        mcp_mode: If True, log to stderr (MCP compatible)

    Example:
        >>> server = DepsSubServer(
        ...     output_dir=Path("LLM-CONTEXT/glintefy/review/deps"),
        ...     repo_path=Path("/path/to/repo"),
        ... )
        >>> result = server.run()
    """

    # License categories
    PERMISSIVE_LICENSES = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "MPL-2.0",
        "WTFPL",
        "Unlicense",
        "CC0-1.0",
        "0BSD",
    }
    COPYLEFT_LICENSES = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"}

    def __init__(
        self,
        name: str = "deps",
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        scan_vulnerabilities: bool | None = None,
        check_licenses: bool | None = None,
        check_outdated: bool | None = None,
        allowed_licenses: list[str] | None = None,
        disallowed_licenses: list[str] | None = None,
        mcp_mode: bool = False,
    ):
        """Initialize deps sub-server."""
        # Get output base from config for standalone use
        base_config = get_config(start_dir=str(repo_path or Path.cwd()))
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")

        if output_dir is None:
            output_dir = Path.cwd() / output_base / name

        super().__init__(name=name, input_dir=output_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mcp_mode = mcp_mode

        # Initialize logger
        if mcp_mode:
            self.logger = get_mcp_logger(f"glintefy.{name}")
        else:
            self.logger = setup_logger(name, log_file=None, level=20)

        # Load config
        config = get_subserver_config("deps", start_dir=str(self.repo_path))
        self.config = config

        # Load reviewer mindset
        self.mindset = get_mindset(DEPS_MINDSET, config)

        # Feature flags
        self.scan_vulnerabilities = scan_vulnerabilities if scan_vulnerabilities is not None else config.get("scan_vulnerabilities", True)
        self.check_licenses = check_licenses if check_licenses is not None else config.get("check_licenses", True)
        self.check_outdated = check_outdated if check_outdated is not None else config.get("check_outdated", True)

        # License configuration
        self.allowed_licenses = allowed_licenses or config.get(
            "allowed_licenses",
            [
                "MIT",
                "Apache-2.0",
                "BSD-2-Clause",
                "BSD-3-Clause",
                "ISC",
                "MPL-2.0",
            ],
        )
        self.disallowed_licenses = disallowed_licenses or config.get("disallowed_licenses", ["GPL-3.0", "AGPL-3.0"])

        # Thresholds
        self.max_age_days = config.get("max_age_days", 365)

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for dependency analysis."""
        missing = []

        # Check for dependency files
        dep_files = [
            self.repo_path / "pyproject.toml",
            self.repo_path / "requirements.txt",
            self.repo_path / "setup.py",
            self.repo_path / "package.json",
            self.repo_path / "Cargo.toml",
            self.repo_path / "go.mod",
            self.repo_path / "Gemfile",
        ]

        if not any(f.exists() for f in dep_files):
            missing.append("No dependency files found (pyproject.toml, requirements.txt, etc.)")

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute dependency analysis."""
        log_section(self.logger, "DEPENDENCY ANALYSIS")

        try:
            ensure_tools_venv()
            log_step(self.logger, 0, "Ensuring tools venv")

            # Initialize results
            results = self._init_results()
            all_issues: list[BaseIssue] = []

            # Detect project type
            log_step(self.logger, 1, "Detecting project type")
            project_type = self._detect_project_type()
            results["project_type"] = project_type

            if not project_type:
                return self._create_no_deps_result()

            # Run analysis steps
            self._run_vulnerability_scan(project_type, results, all_issues)
            self._run_outdated_check(project_type, results, all_issues)
            self._run_license_check(project_type, results, all_issues)
            self._run_dependency_tree(project_type, results)

            # Save and generate results
            log_step(self.logger, 6, "Saving results")
            artifacts = self._save_results(results, all_issues)
            summary = self._generate_summary(results, all_issues)
            status = self._determine_status(all_issues)

            log_result(
                self.logger,
                status != "FAILED",
                f"Analysis complete: {len(all_issues)} issues found",
            )

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=self._compile_metrics(results, all_issues),
            )

        except Exception as e:
            return self._handle_error(e)

    def _init_results(self) -> dict[str, Any]:
        """Initialize results dictionary."""
        return {
            "project_type": None,
            "vulnerabilities": [],
            "outdated": [],
            "licenses": [],
            "dependency_tree": DependencyTree(),
        }

    def _create_no_deps_result(self) -> SubServerResult:
        """Create result when no dependencies found."""
        return SubServerResult(
            status="SUCCESS",
            summary="# Dependency Analysis\n\nNo supported dependency files found.",
            artifacts={},
            metrics={"project_type": None, "total_dependencies": 0},
        )

    def _run_vulnerability_scan(self, project_type: str, results: dict[str, Any], all_issues: list[BaseIssue]) -> None:
        """Run vulnerability scanning if enabled."""
        if not self.scan_vulnerabilities:
            return

        log_step(self.logger, 2, "Scanning for vulnerabilities")
        with LogContext(self.logger, "Vulnerability scan"):
            vuln_results = scan_vulnerabilities(project_type, self.repo_path, self.logger)
            # Convert typed objects to issues first (typed access)
            all_issues.extend(self._vulnerabilities_to_issues(vuln_results))
            # Store as dicts for JSON serialization
            results["vulnerabilities"] = [v.model_dump() for v in vuln_results]

    def _run_outdated_check(self, project_type: str, results: dict[str, Any], all_issues: list[BaseIssue]) -> None:
        """Run outdated package check if enabled."""
        if not self.check_outdated:
            return

        log_step(self.logger, 3, "Checking for outdated packages")
        with LogContext(self.logger, "Outdated check"):
            outdated = check_outdated_packages(project_type, self.repo_path, self.logger)
            # Convert typed objects to issues first (typed access)
            all_issues.extend(self._outdated_to_issues(outdated))
            # Store as dicts for JSON serialization
            results["outdated"] = [pkg.model_dump() for pkg in outdated]

    def _run_license_check(self, project_type: str, results: dict[str, Any], all_issues: list[BaseIssue]) -> None:
        """Run license compliance check if enabled."""
        if not self.check_licenses:
            return

        log_step(self.logger, 4, "Checking license compliance")
        with LogContext(self.logger, "License check"):
            licenses = self._check_licenses(project_type)
            results["licenses"] = licenses
            all_issues.extend(self._licenses_to_issues(licenses))

    def _run_dependency_tree(self, project_type: str, results: dict[str, Any]) -> None:
        """Analyze dependency tree."""
        log_step(self.logger, 5, "Analyzing dependency tree")
        with LogContext(self.logger, "Dependency tree"):
            results["dependency_tree"] = self._get_dependency_tree(project_type)

    def _determine_status(self, all_issues: list[BaseIssue]) -> str:
        """Determine analysis status from issues."""
        critical_count = len([i for i in all_issues if i.severity == "critical"])
        if critical_count > 0:
            return "FAILED"
        if any(i.severity == "warning" for i in all_issues):
            return "PARTIAL"
        return "SUCCESS"

    def _handle_error(self, e: Exception) -> SubServerResult:
        """Handle analysis error."""
        log_error_detailed(
            self.logger,
            e,
            context={"repo_path": str(self.repo_path)},
            include_traceback=True,
        )
        return SubServerResult(
            status="FAILED",
            summary=f"# Dependency Analysis Failed\n\n**Error**: {e}",
            artifacts={},
            errors=[str(e)],
        )

    def _detect_project_type(self) -> str | None:
        """Detect project type from dependency files."""
        if (self.repo_path / "pyproject.toml").exists():
            return "python"
        if (self.repo_path / "requirements.txt").exists():
            return "python"
        if (self.repo_path / "setup.py").exists():
            return "python"
        if (self.repo_path / "package.json").exists():
            return "nodejs"
        if (self.repo_path / "Cargo.toml").exists():
            return "rust"
        if (self.repo_path / "go.mod").exists():
            return "go"
        if (self.repo_path / "Gemfile").exists():
            return "ruby"
        return None

    def _check_licenses(self, project_type: str) -> list[dict[str, Any]]:
        """Check license compliance."""
        licenses = []

        if project_type == "python":
            try:
                python_path = get_tool_path("python")
                pip_licenses_timeout = get_timeout("tool_analysis", 120, start_dir=str(self.repo_path))
                result = subprocess.run(
                    [str(python_path), "-m", "pip_licenses", "--format=json"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=pip_licenses_timeout,
                )
                if result.stdout.strip():
                    licenses = json.loads(result.stdout)
            except FileNotFoundError:
                self.logger.info("pip-licenses not available")
            except Exception as e:
                self.logger.warning(f"license check error: {e}")

        return licenses

    def _get_dependency_tree(self, project_type: str) -> DependencyTree:
        """Get dependency tree."""
        tree = DependencyTree()

        if project_type == "python":
            try:
                pip_list_timeout = get_timeout("tool_quick", 60, start_dir=str(self.repo_path))
                result = subprocess.run(
                    ["pip", "list", "--format=json"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=pip_list_timeout,
                )
                if result.stdout.strip():
                    packages = json.loads(result.stdout)
                    tree.total = len(packages)
                    # Estimate direct deps from requirements/pyproject
                    tree.direct = self._count_direct_deps()
                    tree.depth = 1 if tree.total > 0 else 0
            except Exception as e:
                self.logger.warning(f"dependency tree error: {e}")

        return tree

    def _count_direct_deps(self) -> int:
        """Count direct dependencies from config files."""
        count = 0

        # Check pyproject.toml
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                content = pyproject.read_text()
                data = tomllib.loads(content)
                deps = data.get("project", {}).get("dependencies", [])
                count = len(deps)
            except Exception:
                pass

        # Check requirements.txt
        if count == 0:
            req_file = self.repo_path / "requirements.txt"
            if req_file.exists():
                lines = req_file.read_text().strip().split("\n")
                count = len([line for line in lines if line.strip() and not line.startswith("#")])

        return count

    def _vulnerabilities_to_issues(self, vulns: list[Vulnerability]) -> list[BaseIssue]:
        """Convert vulnerabilities to issues."""
        issues: list[BaseIssue] = []
        for v in vulns:
            issue = VulnerabilityIssue(
                type="vulnerability",
                severity="critical" if v.severity in ("critical", "high") else "warning",
                package=v.package,
                version=v.version,
                vuln_id=v.vulnerability_id,
                message=f"Security vulnerability in {v.package} {v.version}: {v.description[:100]}",
            )
            issues.append(issue)
        return issues

    def _outdated_to_issues(self, outdated: list[OutdatedPackage]) -> list[BaseIssue]:
        """Convert outdated packages to issues."""
        issues: list[BaseIssue] = []
        for pkg in outdated:
            issue = OutdatedIssue(
                type="outdated",
                severity="warning",
                package=pkg.name,
                version=pkg.version,
                latest=pkg.latest_version,
                message=f"Outdated package: {pkg.name} {pkg.version} -> {pkg.latest_version}",
            )
            issues.append(issue)
        return issues

    def _licenses_to_issues(self, licenses: list[dict]) -> list[BaseIssue]:
        """Convert license info to issues."""
        issues: list[BaseIssue] = []
        for lic in licenses:
            license_name = lic.get("License", "")
            if license_name in self.disallowed_licenses:
                issue = LicenseIssue(
                    type="license",
                    severity="critical",
                    package=lic.get("Name", ""),
                    license=license_name,
                    message=f"Disallowed license: {lic.get('Name', '')} uses {license_name}",
                )
                issues.append(issue)
            elif license_name not in self.allowed_licenses and license_name not in self.PERMISSIVE_LICENSES:
                issue = LicenseIssue(
                    type="license",
                    severity="warning",
                    package=lic.get("Name", ""),
                    license=license_name,
                    message=f"Unknown license: {lic.get('Name', '')} uses {license_name}",
                )
                issues.append(issue)
        return issues

    def _save_results(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Path]:
        """Save all results to files."""
        artifacts = {}

        # Vulnerabilities
        if results.get("vulnerabilities"):
            path = self.output_dir / "vulnerabilities.json"
            path.write_text(json.dumps(results["vulnerabilities"], indent=2))
            artifacts["vulnerabilities"] = path

        # Outdated
        if results.get("outdated"):
            path = self.output_dir / "outdated.json"
            path.write_text(json.dumps(results["outdated"], indent=2))
            artifacts["outdated"] = path

        # Licenses
        if results.get("licenses"):
            path = self.output_dir / "licenses.json"
            path.write_text(json.dumps(results["licenses"], indent=2))
            artifacts["licenses"] = path

        # Dependency tree
        tree = results.get("dependency_tree")
        if tree:
            path = self.output_dir / "dependency_tree.json"
            tree_dict = tree.to_dict() if isinstance(tree, DependencyTree) else tree
            path.write_text(json.dumps(tree_dict, indent=2))
            artifacts["dependency_tree"] = path

        # All issues (convert dataclasses to dicts)
        if all_issues:
            report_dir = self.output_dir.parent / "report"

            # Get unique issue types before conversion (typed access)
            issue_types = list({issue.type for issue in all_issues})

            # Cleanup old chunked files
            cleanup_chunked_issues(
                output_dir=report_dir,
                issue_types=issue_types,
                prefix="issues",
            )

            # Convert to dicts at serialization boundary
            issues_dicts = [issue.to_dict() for issue in all_issues]

            # Write chunked issues
            written_files = write_chunked_issues(
                issues=issues_dicts,
                output_dir=report_dir,
                prefix="issues",
            )

            if written_files:
                artifacts["issues"] = written_files[0]

        return artifacts

    def _compile_metrics(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> dict[str, Any]:
        """Compile metrics for result."""
        tree = results.get("dependency_tree")
        total_deps = tree.total if isinstance(tree, DependencyTree) else tree.get("total", 0) if tree else 0
        direct_deps = tree.direct if isinstance(tree, DependencyTree) else tree.get("direct", 0) if tree else 0

        return DepsMetrics(
            project_type=results.get("project_type"),
            total_dependencies=total_deps,
            direct_dependencies=direct_deps,
            vulnerabilities_count=len(results.get("vulnerabilities", [])),
            outdated_count=len(results.get("outdated", [])),
            license_issues=len([i for i in all_issues if i.type == "license"]),
            critical_issues=len([i for i in all_issues if i.severity == "critical"]),
            total_issues=len(all_issues),
        ).model_dump()

    def _generate_summary(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> str:
        """Generate markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(results, all_issues)
        verdict = self._evaluate_mindset(all_issues, metrics)

        lines = []
        lines.extend(self._format_header_section(verdict, metrics, results))
        lines.extend(self._format_vulnerabilities_section(results))
        lines.extend(self._format_outdated_section(results))
        lines.extend(self._format_license_section(all_issues))
        lines.extend(self._format_approval_section(verdict))

        return "\n".join(lines)

    def _evaluate_mindset(self, all_issues: list[BaseIssue], metrics: dict[str, Any]) -> Any:
        """Evaluate results using mindset."""
        critical_issues = [i for i in all_issues if i.severity == "critical"]
        warning_issues = [i for i in all_issues if i.severity == "warning"]
        total_items = max(metrics["total_dependencies"], 1)

        return evaluate_results(
            self.mindset,
            critical_issues,
            warning_issues,
            total_items,
        )

    def _format_header_section(self, verdict: Any, metrics: dict[str, Any], results: dict[str, Any]) -> list[str]:
        """Format header section with mindset, verdict, and overview."""
        tree = results.get("dependency_tree")
        tree_total = tree.total if isinstance(tree, DependencyTree) else tree.get("total", 0) if tree else 0
        tree_direct = tree.direct if isinstance(tree, DependencyTree) else tree.get("direct", 0) if tree else 0

        return [
            "# Dependency Analysis Report",
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
            f"- Critical issues: {verdict.critical_count} ({verdict.critical_ratio:.1f}%)",
            f"- Warnings: {verdict.warning_count} ({verdict.warning_ratio:.1f}%)",
            f"- Total dependencies analyzed: {max(metrics['total_dependencies'], 1)}",
            "",
            "## Overview",
            "",
            f"**Project Type**: {results.get('project_type', 'Unknown')}",
            f"**Total Dependencies**: {tree_total}",
            f"**Direct Dependencies**: {tree_direct}",
            f"**Total Issues**: {metrics['total_issues']}",
            "",
            "## Security Vulnerabilities",
            "",
        ]

    def _format_vulnerabilities_section(self, results: dict[str, Any]) -> list[str]:
        """Format security vulnerabilities section."""
        lines = []
        vulns = results.get("vulnerabilities", [])

        if vulns:
            limit = get_display_limit("max_vulnerabilities", 10, start_dir=str(self.repo_path))
            display_count = len(vulns) if limit is None else min(limit, len(vulns))

            header = f"[HIGH] **{len(vulns)} vulnerabilities found**"
            if limit is not None and len(vulns) > limit:
                header += f" (showing {display_count})"
            lines.append(header + "\n")

            for v in vulns[:limit]:
                lines.append(f"- **{v.get('package', '')}** {v.get('version', '')}: {v.get('vulnerability_id', '')} - {v.get('description', '')[:80]}")

            if limit is not None and len(vulns) > limit:
                lines.append("")
                lines.append(
                    f"*Note: {len(vulns) - limit} more vulnerabilities not shown. Set `output.display.max_vulnerabilities = 0` in config for unlimited display.*"
                )
        else:
            lines.append("[PASS] No known vulnerabilities found")

        lines.append("")
        return lines

    def _format_outdated_section(self, results: dict[str, Any]) -> list[str]:
        """Format outdated packages section."""
        lines = ["## Outdated Packages\n"]
        outdated = results.get("outdated", [])

        if outdated:
            limit = get_display_limit("max_outdated_packages", 10, start_dir=str(self.repo_path))
            display_count = len(outdated) if limit is None else min(limit, len(outdated))

            header = f"[WARN] **{len(outdated)} packages are outdated**"
            if limit is not None and len(outdated) > limit:
                header += f" (showing {display_count})"
            lines.append(header + "\n")

            for pkg in outdated[:limit]:
                lines.append(f"- **{pkg.get('name', '')}**: {pkg.get('version', '')} -> {pkg.get('latest_version', '')}")

            if limit is not None and len(outdated) > limit:
                lines.append("")
                lines.append(
                    f"*Note: {len(outdated) - limit} more outdated packages not shown. Set `output.display.max_outdated_packages = 0` in config for unlimited display.*"
                )
        else:
            lines.append("[PASS] All packages are up to date")

        lines.append("")
        return lines

    def _format_license_section(self, all_issues: list[BaseIssue]) -> list[str]:
        """Format license compliance section."""
        lines = ["## License Compliance\n"]
        license_issues = [i for i in all_issues if i.type == "license"]

        if license_issues:
            limit = get_display_limit("max_license_issues", 5, start_dir=str(self.repo_path))
            display_count = len(license_issues) if limit is None else min(limit, len(license_issues))

            header = f"[WARN] **{len(license_issues)} license issues found**"
            if limit is not None and len(license_issues) > limit:
                header += f" (showing {display_count})"
            lines.append(header + "\n")

            for lic in license_issues[:limit]:
                lines.append(f"- {lic.message}")

            if limit is not None and len(license_issues) > limit:
                lines.append("")
                lines.append(
                    f"*Note: {len(license_issues) - limit} more license issues not shown. Set `output.display.max_license_issues = 0` in config for unlimited display.*"
                )
        else:
            lines.append("[PASS] All licenses are compliant")

        lines.append("")
        return lines

    def _format_approval_section(self, verdict: Any) -> list[str]:
        """Format approval status section."""
        lines = ["## Approval Status", "", f"**{verdict.verdict_text}**"]

        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")

        return lines
