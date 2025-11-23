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


def run_pip_audit(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run pip-audit for Python vulnerability scanning."""
    vulnerabilities = []
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

        if result.stdout.strip():
            try:
                audit_results = json.loads(result.stdout)
                for dep in audit_results.get("dependencies", []):
                    for vuln in dep.get("vulns", []):
                        vulnerabilities.append(
                            {
                                "package": dep.get("name", ""),
                                "version": dep.get("version", ""),
                                "vulnerability_id": vuln.get("id", ""),
                                "description": vuln.get("description", ""),
                                "fix_versions": vuln.get("fix_versions", []),
                                "severity": classify_vuln_severity(vuln),
                            }
                        )
            except json.JSONDecodeError:
                logger.warning("Failed to parse pip-audit output")

    except FileNotFoundError:
        logger.info("pip-audit not available")
    except subprocess.TimeoutExpired:
        logger.warning("pip-audit timed out")
    except Exception as e:
        logger.warning(f"pip-audit error: {e}")

    return vulnerabilities


def run_safety(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run safety for Python vulnerability scanning."""
    vulnerabilities = []
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

        if result.stdout.strip():
            try:
                safety_results = json.loads(result.stdout)
                for vuln in safety_results:
                    vulnerabilities.append(
                        {
                            "package": vuln[0] if len(vuln) > 0 else "",
                            "version": vuln[2] if len(vuln) > 2 else "",
                            "vulnerability_id": vuln[4] if len(vuln) > 4 else "",
                            "description": vuln[3] if len(vuln) > 3 else "",
                            "severity": "high",
                        }
                    )
            except json.JSONDecodeError:
                pass

    except FileNotFoundError:
        logger.info("safety not available")
    except Exception as e:
        logger.warning(f"safety error: {e}")

    return vulnerabilities


def run_npm_audit(repo_path: Path, logger: Logger) -> list[dict[str, Any]]:
    """Run npm audit for Node.js vulnerability scanning."""
    vulnerabilities = []
    try:
        timeout = get_timeout("vuln_scan", 120)
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_path),
        )

        if result.stdout.strip():
            try:
                audit_results = json.loads(result.stdout)
                for vuln_id, vuln in audit_results.get("vulnerabilities", {}).items():
                    vulnerabilities.append(
                        {
                            "package": vuln_id,
                            "version": vuln.get("range", ""),
                            "vulnerability_id": "",
                            "description": vuln.get("title", ""),
                            "severity": vuln.get("severity", "moderate"),
                        }
                    )
            except json.JSONDecodeError:
                pass

    except FileNotFoundError:
        logger.info("npm not available")
    except Exception as e:
        logger.warning(f"npm audit error: {e}")

    return vulnerabilities


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


def check_outdated_packages(
    project_type: str,
    repo_path: Path,
    logger: Logger,
) -> list[dict[str, Any]]:
    """Check for outdated packages."""
    outdated = []

    if project_type == "python":
        try:
            timeout = get_timeout("tool_analysis", 60)
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.stdout.strip():
                outdated = json.loads(result.stdout)
        except Exception as e:
            logger.warning(f"pip outdated check error: {e}")

    elif project_type == "nodejs":
        try:
            timeout = get_timeout("tool_analysis", 60)
            result = subprocess.run(
                ["npm", "outdated", "--json"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(repo_path),
            )
            if result.stdout.strip():
                npm_outdated = json.loads(result.stdout)
                for pkg, info in npm_outdated.items():
                    outdated.append(
                        {
                            "name": pkg,
                            "version": info.get("current", ""),
                            "latest_version": info.get("latest", ""),
                        }
                    )
        except Exception as e:
            logger.warning(f"npm outdated check error: {e}")

    return outdated
