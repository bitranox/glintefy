"""Dependency scanning utilities.

Extracted from DepsSubServer to reduce class size.
"""

import json
import subprocess
from logging import Logger
from pathlib import Path
from typing import Any

from btx_fix_mcp.tools_venv import get_tool_path
from btx_fix_mcp.config import get_timeout


def scan_vulnerabilities(
    project_type: str,
    repo_path: Path,
    logger: Logger,
) -> list[dict[str, Any]]:
    """Scan for known vulnerabilities in dependencies."""
    if project_type == "python":
        vulns = run_pip_audit(repo_path, logger)
        if not vulns:
            vulns = run_safety(repo_path, logger)
        return vulns
    elif project_type == "nodejs":
        return run_npm_audit(repo_path, logger)
    return []


def _parse_pip_audit_vuln(dep: dict, vuln: dict) -> dict[str, Any]:
    """Parse a single vulnerability from pip-audit output."""
    return {
        "package": dep.get("name", ""),
        "version": dep.get("version", ""),
        "vulnerability_id": vuln.get("id", ""),
        "description": vuln.get("description", ""),
        "fix_versions": vuln.get("fix_versions", []),
        "severity": classify_vuln_severity(vuln),
    }


def _extract_pip_audit_vulns(audit_results: dict) -> list[dict[str, Any]]:
    """Extract vulnerabilities from pip-audit JSON results."""
    vulnerabilities = []
    for dep in audit_results.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            vulnerabilities.append(_parse_pip_audit_vuln(dep, vuln))
    return vulnerabilities


def _parse_pip_audit_output(output: str, logger: Logger) -> list[dict[str, Any]]:
    """Parse pip-audit JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        audit_results = json.loads(output)
        return _extract_pip_audit_vulns(audit_results)
    except json.JSONDecodeError:
        logger.warning("Failed to parse pip-audit output")
        return []


def run_pip_audit(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run pip-audit for Python vulnerability scanning."""
    try:
        python_path = get_tool_path("python")
        timeout = get_timeout("vuln_scan", 120)
        result = subprocess.run(
            [str(python_path), "-m", "pip_audit", "--format=json", "--strict"],
            capture_output=True,
            text=True,
            timeout=timeout,
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


def _parse_safety_vuln(vuln: list) -> dict[str, Any]:
    """Parse a single vulnerability from safety output."""
    return {
        "package": vuln[0] if len(vuln) > 0 else "",
        "version": vuln[2] if len(vuln) > 2 else "",
        "vulnerability_id": vuln[4] if len(vuln) > 4 else "",
        "description": vuln[3] if len(vuln) > 3 else "",
        "severity": "high",
    }


def _parse_safety_output(output: str) -> list[dict[str, Any]]:
    """Parse safety JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        safety_results = json.loads(output)
        return [_parse_safety_vuln(vuln) for vuln in safety_results]
    except json.JSONDecodeError:
        return []


def run_safety(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run safety for Python vulnerability scanning."""
    try:
        python_path = get_tool_path("python")
        timeout = get_timeout("vuln_scan", 120)
        result = subprocess.run(
            [str(python_path), "-m", "safety", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_path),
        )
        return _parse_safety_output(result.stdout)

    except FileNotFoundError:
        logger.info("safety not available")
    except Exception as e:
        logger.warning(f"safety error: {e}")

    return []


def _parse_npm_vuln(vuln_id: str, vuln: dict) -> dict[str, Any]:
    """Parse a single vulnerability from npm audit output."""
    return {
        "package": vuln_id,
        "version": vuln.get("range", ""),
        "vulnerability_id": "",
        "description": vuln.get("title", ""),
        "severity": vuln.get("severity", "moderate"),
    }


def _parse_npm_audit_output(output: str) -> list[dict[str, Any]]:
    """Parse npm audit JSON output into vulnerability list."""
    if not output.strip():
        return []

    try:
        audit_results = json.loads(output)
        return [_parse_npm_vuln(vuln_id, vuln) for vuln_id, vuln in audit_results.get("vulnerabilities", {}).items()]
    except json.JSONDecodeError:
        return []


def run_npm_audit(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run npm audit for Node.js vulnerability scanning."""
    try:
        timeout = get_timeout("vuln_scan", 120)
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_path),
        )
        return _parse_npm_audit_output(result.stdout)

    except FileNotFoundError:
        logger.info("npm not available")
    except Exception as e:
        logger.warning(f"npm audit error: {e}")

    return []


def classify_vuln_severity(vuln: dict) -> str:
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


def _check_python_outdated(logger: Logger) -> list[dict[str, Any]]:
    """Check for outdated Python packages."""
    try:
        timeout = get_timeout("tool_analysis", 60)
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"pip outdated check error: {e}")

    return []


def _parse_npm_outdated_entry(pkg: str, info: dict) -> dict[str, Any]:
    """Parse a single npm outdated entry."""
    return {
        "name": pkg,
        "version": info.get("current", ""),
        "latest_version": info.get("latest", ""),
    }


def _check_nodejs_outdated(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Check for outdated Node.js packages."""
    try:
        timeout = get_timeout("tool_analysis", 60)
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
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
) -> list[dict[str, Any]]:
    """Check for outdated packages."""
    if project_type == "python":
        return _check_python_outdated(logger)
    if project_type == "nodejs":
        return _check_nodejs_outdated(repo_path, logger)
    return []
