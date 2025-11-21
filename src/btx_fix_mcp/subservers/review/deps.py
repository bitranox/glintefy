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

from btx_fix_mcp.config import get_config, get_subserver_config
from btx_fix_mcp.subservers.common.issues import (
    BaseIssue,
    DependencyTree,
    DepsMetrics,
    LicenseIssue,
    OutdatedIssue,
    VulnerabilityIssue,
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
    DEPS_MINDSET,
    evaluate_results,
    get_mindset,
)
from btx_fix_mcp.subservers.review.deps_scanners import (
    check_outdated_packages,
    scan_vulnerabilities,
)
from btx_fix_mcp.tools_venv import ensure_tools_venv, get_tool_path


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
        ...     output_dir=Path("LLM-CONTEXT/btx_fix_mcp/review/deps"),
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
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/btx_fix_mcp/review")

        if output_dir is None:
            output_dir = Path.cwd() / output_base / name

        super().__init__(name=name, input_dir=output_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mcp_mode = mcp_mode

        # Initialize logger
        if mcp_mode:
            self.logger = get_mcp_logger(f"btx_fix_mcp.{name}")
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
            # Ensure tools venv
            log_step(self.logger, 0, "Ensuring tools venv")
            ensure_tools_venv()

            results: dict[str, Any] = {
                "project_type": None,
                "vulnerabilities": [],
                "outdated": [],
                "licenses": [],
                "dependency_tree": DependencyTree(),
            }
            all_issues: list[BaseIssue] = []

            # Step 1: Detect project type
            log_step(self.logger, 1, "Detecting project type")
            project_type = self._detect_project_type()
            results["project_type"] = project_type

            if not project_type:
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Dependency Analysis\n\nNo supported dependency files found.",
                    artifacts={},
                    metrics={"project_type": None, "total_dependencies": 0},
                )

            # Step 2: Vulnerability scanning
            if self.scan_vulnerabilities:
                log_step(self.logger, 2, "Scanning for vulnerabilities")
                with LogContext(self.logger, "Vulnerability scan"):
                    vuln_results = scan_vulnerabilities(project_type, self.repo_path, self.logger)
                    results["vulnerabilities"] = vuln_results
                    all_issues.extend(self._vulnerabilities_to_issues(vuln_results))

            # Step 3: Outdated package detection
            if self.check_outdated:
                log_step(self.logger, 3, "Checking for outdated packages")
                with LogContext(self.logger, "Outdated check"):
                    outdated = check_outdated_packages(project_type, self.repo_path, self.logger)
                    results["outdated"] = outdated
                    all_issues.extend(self._outdated_to_issues(outdated))

            # Step 4: License compliance
            if self.check_licenses:
                log_step(self.logger, 4, "Checking license compliance")
                with LogContext(self.logger, "License check"):
                    licenses = self._check_licenses(project_type)
                    results["licenses"] = licenses
                    all_issues.extend(self._licenses_to_issues(licenses))

            # Step 5: Dependency tree
            log_step(self.logger, 5, "Analyzing dependency tree")
            with LogContext(self.logger, "Dependency tree"):
                results["dependency_tree"] = self._get_dependency_tree(project_type)

            # Step 6: Save results
            log_step(self.logger, 6, "Saving results")
            artifacts = self._save_results(results, all_issues)

            # Step 7: Generate summary
            summary = self._generate_summary(results, all_issues)

            # Determine status
            critical_count = len([i for i in all_issues if i.severity == "critical"])
            status = "FAILED" if critical_count > 0 else "SUCCESS"
            if not critical_count and any(i.severity == "warning" for i in all_issues):
                status = "PARTIAL"

            log_result(self.logger, status != "FAILED", f"Analysis complete: {len(all_issues)} issues found")

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=self._compile_metrics(results, all_issues),
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
                result = subprocess.run(
                    [str(python_path), "-m", "pip_licenses", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
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
                result = subprocess.run(
                    ["pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
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

    def _vulnerabilities_to_issues(self, vulns: list[dict]) -> list[BaseIssue]:
        """Convert vulnerabilities to issues."""
        issues: list[BaseIssue] = []
        for v in vulns:
            issue = VulnerabilityIssue(
                type="vulnerability",
                severity="critical" if v.get("severity") in ("critical", "high") else "warning",
                package=v.get("package", ""),
                version=v.get("version", ""),
                vuln_id=v.get("vulnerability_id", ""),
                message=f"Security vulnerability in {v.get('package', '')} {v.get('version', '')}: {v.get('description', '')[:100]}",
            )
            issues.append(issue)
        return issues

    def _outdated_to_issues(self, outdated: list[dict]) -> list[BaseIssue]:
        """Convert outdated packages to issues."""
        issues: list[BaseIssue] = []
        for pkg in outdated:
            issue = OutdatedIssue(
                type="outdated",
                severity="warning",
                package=pkg.get("name", ""),
                version=pkg.get("version", ""),
                latest=pkg.get("latest_version", ""),
                message=f"Outdated package: {pkg.get('name', '')} {pkg.get('version', '')} -> {pkg.get('latest_version', '')}",
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
            path = self.output_dir / "issues.json"
            issues_dicts = [issue.to_dict() for issue in all_issues]
            path.write_text(json.dumps(issues_dicts, indent=2))
            artifacts["issues"] = path

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
        ).to_dict()

    def _generate_summary(self, results: dict[str, Any], all_issues: list[BaseIssue]) -> str:
        """Generate markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(results, all_issues)
        tree = results.get("dependency_tree")
        tree_total = tree.total if isinstance(tree, DependencyTree) else tree.get("total", 0) if tree else 0
        tree_direct = tree.direct if isinstance(tree, DependencyTree) else tree.get("direct", 0) if tree else 0

        # Evaluate results with mindset (convert to dicts for evaluate_results)
        critical_issues = [i.to_dict() for i in all_issues if i.severity == "critical"]
        warning_issues = [i.to_dict() for i in all_issues if i.severity == "warning"]
        total_items = max(metrics["total_dependencies"], 1)

        verdict = evaluate_results(
            self.mindset,
            critical_issues,
            warning_issues,
            total_items,
        )

        lines = [
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
            f"- Total dependencies analyzed: {total_items}",
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

        vulns = results.get("vulnerabilities", [])
        if vulns:
            lines.append(f"🔴 **{len(vulns)} vulnerabilities found**\n")
            for v in vulns[:10]:
                lines.append(f"- **{v.get('package', '')}** {v.get('version', '')}: {v.get('vulnerability_id', '')} - {v.get('description', '')[:80]}")
            if len(vulns) > 10:
                lines.append(f"- ... and {len(vulns) - 10} more")
        else:
            lines.append("✅ No known vulnerabilities found")
        lines.append("")

        # Outdated packages
        lines.append("## Outdated Packages\n")
        outdated = results.get("outdated", [])
        if outdated:
            lines.append(f"⚠️ **{len(outdated)} packages are outdated**\n")
            for pkg in outdated[:10]:
                lines.append(f"- **{pkg.get('name', '')}**: {pkg.get('version', '')} → {pkg.get('latest_version', '')}")
            if len(outdated) > 10:
                lines.append(f"- ... and {len(outdated) - 10} more")
        else:
            lines.append("✅ All packages are up to date")
        lines.append("")

        # License compliance
        lines.append("## License Compliance\n")
        license_issues = [i for i in all_issues if i.type == "license"]
        if license_issues:
            lines.append(f"⚠️ **{len(license_issues)} license issues found**\n")
            for lic in license_issues[:5]:
                lines.append(f"- {lic.message}")
        else:
            lines.append("✅ All licenses are compliant")
        lines.append("")

        # Approval status
        lines.extend(["## Approval Status", ""])
        lines.append(f"**{verdict.verdict_text}**")
        if verdict.recommendations:
            lines.append("")
            for rec in verdict.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)
