"""Dependency scanning utilities.

Extracted from DepsSubServer to reduce class size.
"""

import json
import subprocess
from logging import Logger
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from glintefy.config import get_timeout
from glintefy.tools_venv import get_tool_path


# --- Pydantic Models for Vulnerability Data ---


class Vulnerability(BaseModel):
    """Typed representation of a dependency vulnerability."""

    model_config = ConfigDict(extra="ignore")

    package: str = ""
    version: str = ""
    vulnerability_id: str = ""
    description: str = ""
    fix_versions: list[str] = Field(default_factory=list)
    severity: Literal["critical", "high", "medium", "low"] = "high"


class OutdatedPackage(BaseModel):
    """Typed representation of an outdated package."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    version: str = ""
    latest_version: str = ""


def scan_vulnerabilities(
    project_type: str,
    repo_path: Path,
    logger: Logger,
) -> list[Vulnerability]:
    """Scan for known vulnerabilities in dependencies."""
    if project_type == "python":
        vulns = run_pip_audit(repo_path, logger)
        if not vulns:
            vulns = run_safety(repo_path, logger)
        return vulns
    if project_type == "nodejs":
        return run_npm_audit(repo_path, logger)
    return []


def _parse_pip_audit_vuln(dep: dict, vuln: dict) -> Vulnerability:
    """Parse a single vulnerability from pip-audit output."""
    return Vulnerability(
        package=dep.get("name", ""),
        version=dep.get("version", ""),
        vulnerability_id=vuln.get("id", ""),
        description=vuln.get("description", ""),
        fix_versions=vuln.get("fix_versions", []),
        severity=classify_vuln_severity(vuln),
    )


def _extract_pip_audit_vulns(audit_results: dict) -> list[Vulnerability]:
    """Extract vulnerabilities from pip-audit JSON results."""
    vulnerabilities = []
    for dep in audit_results.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            vulnerabilities.append(_parse_pip_audit_vuln(dep, vuln))
    return vulnerabilities


def _parse_pip_audit_output(output: str, logger: Logger) -> list[Vulnerability]:
    """Parse pip-audit JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        audit_results = json.loads(output)
        return _extract_pip_audit_vulns(audit_results)
    except json.JSONDecodeError:
        logger.warning("Failed to parse pip-audit output")
        return []


def run_pip_audit(repo_path: Path, logger: Logger) -> list[Vulnerability]:
    """Run pip-audit for Python vulnerability scanning."""
    try:
        python_path = get_tool_path("python")
        pip_audit_timeout = get_timeout("vuln_scan", 240)
        result = subprocess.run(
            [str(python_path), "-m", "pip_audit", "--format=json", "--strict"],
            check=False,
            capture_output=True,
            text=True,
            timeout=pip_audit_timeout,
            cwd=str(repo_path),
        )
        return _parse_pip_audit_output(result.stdout, logger)

    except FileNotFoundError:
        logger.info("pip-audit not available")
    except subprocess.TimeoutExpired:
        logger.warning("pip-audit timed out")
    except Exception as e:
        logger.warning(f"pip-audit error: {e}")

    return []


def _normalize_severity(severity: str) -> Literal["critical", "high", "medium", "low"]:
    """Normalize severity string to valid enum value."""
    severity_lower = severity.lower()
    if severity_lower in ("critical",):
        return "critical"
    if severity_lower in ("high",):
        return "high"
    if severity_lower in ("medium", "moderate"):
        return "medium"
    if severity_lower in ("low",):
        return "low"
    return "high"  # Default to high for unknown


def _parse_safety_vuln(vuln: list) -> Vulnerability:
    """Parse a single vulnerability from safety output."""
    return Vulnerability(
        package=vuln[0] if len(vuln) > 0 else "",
        version=vuln[2] if len(vuln) > 2 else "",
        vulnerability_id=vuln[4] if len(vuln) > 4 else "",
        description=vuln[3] if len(vuln) > 3 else "",
        severity="high",
    )


def _parse_safety_output(output: str) -> list[Vulnerability]:
    """Parse safety JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        safety_results = json.loads(output)
        return [_parse_safety_vuln(vuln) for vuln in safety_results]
    except json.JSONDecodeError:
        return []


def run_safety(repo_path: Path, logger: Logger) -> list[Vulnerability]:
    """Run safety for Python vulnerability scanning."""
    try:
        python_path = get_tool_path("python")
        safety_timeout = get_timeout("vuln_scan", 240)
        result = subprocess.run(
            [str(python_path), "-m", "safety", "check", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=safety_timeout,
            cwd=str(repo_path),
        )
        return _parse_safety_output(result.stdout)

    except FileNotFoundError:
        logger.info("safety not available")
    except Exception as e:
        logger.warning(f"safety error: {e}")

    return []


def _parse_npm_vuln(vuln_id: str, vuln: dict) -> Vulnerability:
    """Parse a single vulnerability from npm audit output."""
    return Vulnerability(
        package=vuln_id,
        version=vuln.get("range", ""),
        vulnerability_id="",
        description=vuln.get("title", ""),
        severity=_normalize_severity(vuln.get("severity", "moderate")),
    )


def _parse_npm_audit_output(output: str) -> list[Vulnerability]:
    """Parse npm audit JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        audit_results = json.loads(output)
        return [_parse_npm_vuln(vuln_id, vuln) for vuln_id, vuln in audit_results.get("vulnerabilities", {}).items()]
    except json.JSONDecodeError:
        return []


def run_npm_audit(repo_path: Path, logger: Logger) -> list[Vulnerability]:
    """Run npm audit for Node.js vulnerability scanning."""
    try:
        npm_audit_timeout = get_timeout("vuln_scan", 240)
        result = subprocess.run(
            ["npm", "audit", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=npm_audit_timeout,
            cwd=str(repo_path),
        )
        return _parse_npm_audit_output(result.stdout)

    except FileNotFoundError:
        logger.info("npm not available")
    except Exception as e:
        logger.warning(f"npm audit error: {e}")

    return []


def classify_vuln_severity(vuln: dict) -> Literal["critical", "high", "medium", "low"]:
    """Classify vulnerability severity."""
    aliases = vuln.get("aliases", [])
    desc = vuln.get("description", "").lower()

    if any("critical" in str(a).lower() for a in aliases):
        return "critical"
    if "remote code execution" in desc or "rce" in desc:
        return "critical"
    if "sql injection" in desc or "command injection" in desc:
        return "critical"

    return "high"


def _get_project_dependencies(repo_path: Path) -> set[str]:
    """Extract project dependencies from pyproject.toml or requirements.txt.

    Returns a set of normalized package names (lowercase, underscores to hyphens).
    """
    deps: set[str] = set()

    # Try pyproject.toml first
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with pyproject.open("rb") as f:
                data = tomllib.load(f)

            # Get main dependencies
            project_deps = data.get("project", {}).get("dependencies", [])
            for dep in project_deps:
                # Extract package name (before any version specifier)
                name = dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0].split(";")[0].strip()
                deps.add(name.lower().replace("_", "-"))

            # Get optional dependencies
            optional = data.get("project", {}).get("optional-dependencies", {})
            for group_deps in optional.values():
                for dep in group_deps:
                    name = dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0].split(";")[0].strip()
                    deps.add(name.lower().replace("_", "-"))

        except Exception:
            pass  # Fall through to requirements.txt

    # Try requirements.txt as fallback
    for req_file in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
        req_path = repo_path / req_file
        if req_path.exists():
            try:
                for line in req_path.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        name = line.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0].split(";")[0].strip()
                        if name:
                            deps.add(name.lower().replace("_", "-"))
            except Exception:
                pass

    return deps


def _check_python_outdated(repo_path: Path, logger: Logger) -> list[OutdatedPackage]:
    """Check for outdated Python packages that are project dependencies."""
    try:
        # Get project dependencies to filter results
        project_deps = _get_project_dependencies(repo_path)

        pip_outdated_timeout = get_timeout("tool_analysis", 120)
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=pip_outdated_timeout,
        )
        if result.stdout.strip():
            raw_packages = json.loads(result.stdout)
            outdated = []
            for pkg in raw_packages:
                name = pkg.get("name", "")
                # Normalize name for comparison
                normalized = name.lower().replace("_", "-")
                # Only include if it's a project dependency (or if we couldn't parse deps)
                if not project_deps or normalized in project_deps:
                    outdated.append(
                        OutdatedPackage(
                            name=name,
                            version=pkg.get("version", ""),
                            latest_version=pkg.get("latest_version", ""),
                        )
                    )
            return outdated
    except Exception as e:
        logger.warning(f"pip outdated check error: {e}")

    return []


def _parse_npm_outdated_entry(pkg: str, info: dict) -> OutdatedPackage:
    """Parse a single npm outdated entry."""
    return OutdatedPackage(
        name=pkg,
        version=info.get("current", ""),
        latest_version=info.get("latest", ""),
    )


def _check_nodejs_outdated(repo_path: Path, logger: Logger) -> list[OutdatedPackage]:
    """Check for outdated Node.js packages."""
    try:
        npm_outdated_timeout = get_timeout("tool_analysis", 120)
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=npm_outdated_timeout,
            cwd=str(repo_path),
        )
        if not result.stdout.strip():
            return []

        npm_outdated = json.loads(result.stdout)
        return [_parse_npm_outdated_entry(pkg, info) for pkg, info in npm_outdated.items()]

    except Exception as e:
        logger.warning(f"npm outdated check error: {e}")

    return []


def check_outdated_packages(
    project_type: str,
    repo_path: Path,
    logger: Logger,
) -> list[OutdatedPackage]:
    """Check for outdated packages."""
    if project_type == "python":
        return _check_python_outdated(repo_path, logger)
    if project_type == "nodejs":
        return _check_nodejs_outdated(repo_path, logger)
    return []
