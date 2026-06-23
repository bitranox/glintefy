"""Tests for deps_scanners module."""

import json
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from glintefy.subservers.review.deps_scanners import (
    check_outdated_packages,
    classify_vuln_severity,
    run_npm_audit,
    run_pip_audit,
    run_safety,
    scan_vulnerabilities,
)


@pytest.fixture
def logger():
    """Create a logger for tests."""
    return logging.getLogger("test_deps_scanners")


class TestScanVulnerabilities:
    """Tests for scan_vulnerabilities function."""

    def test_scan_python_project(self, tmp_path, logger):
        """Test scanning Python project."""
        with patch("glintefy.subservers.review.deps_scanners.run_pip_audit") as mock_pip:
            mock_pip.return_value = [{"package": "requests", "vulnerability_id": "CVE-123"}]

            result = scan_vulnerabilities("python", tmp_path, logger)

            assert len(result) == 1
            mock_pip.assert_called_once()

    def test_scan_python_fallback_to_safety(self, tmp_path, logger):
        """Test fallback to safety when pip-audit returns empty."""
        with patch("glintefy.subservers.review.deps_scanners.run_pip_audit") as mock_pip:
            with patch("glintefy.subservers.review.deps_scanners.run_safety") as mock_safety:
                mock_pip.return_value = []
                mock_safety.return_value = [{"package": "urllib3", "vulnerability_id": "CVE-456"}]

                result = scan_vulnerabilities("python", tmp_path, logger)

                assert len(result) == 1
                mock_pip.assert_called_once()
                mock_safety.assert_called_once()

    def test_scan_nodejs_project(self, tmp_path, logger):
        """Test scanning Node.js project."""
        with patch("glintefy.subservers.review.deps_scanners.run_npm_audit") as mock_npm:
            mock_npm.return_value = [{"package": "lodash", "vulnerability_id": "npm:123"}]

            result = scan_vulnerabilities("nodejs", tmp_path, logger)

            assert len(result) == 1
            mock_npm.assert_called_once()

    def test_scan_unknown_project_type(self, tmp_path, logger):
        """Test scanning unknown project type returns empty."""
        result = scan_vulnerabilities("unknown", tmp_path, logger)

        assert result == []


class TestRunPipAudit:
    """Tests for run_pip_audit function."""

    def test_pip_audit_success(self, tmp_path, logger):
        """Test successful pip-audit run."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {
                "dependencies": [
                    {
                        "name": "requests",
                        "version": "2.25.0",
                        "vulns": [
                            {
                                "id": "CVE-2021-1234",
                                "description": "Security issue",
                                "fix_versions": ["2.26.0"],
                            }
                        ],
                    }
                ]
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            result = run_pip_audit(tmp_path, logger)

            assert len(result) == 1
            assert result[0].package == "requests"
            assert result[0].vulnerability_id == "CVE-2021-1234"

    def test_pip_audit_empty_output(self, tmp_path, logger):
        """Test pip-audit with empty output."""
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = run_pip_audit(tmp_path, logger)

            assert result == []

    def test_pip_audit_invalid_json(self, tmp_path, logger):
        """Test pip-audit with invalid JSON output."""
        mock_result = MagicMock()
        mock_result.stdout = "not valid json"

        with patch("subprocess.run", return_value=mock_result):
            result = run_pip_audit(tmp_path, logger)

            assert result == []

    def test_pip_audit_not_found(self, tmp_path, logger):
        """Test pip-audit not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = run_pip_audit(tmp_path, logger)

            assert result == []

    def test_pip_audit_timeout(self, tmp_path, logger):
        """Test pip-audit timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pip-audit", 120)):
            result = run_pip_audit(tmp_path, logger)

            assert result == []


class TestRunSafety:
    """Tests for run_safety function."""

    def test_safety_success(self, tmp_path, logger):
        """Test successful safety run."""
        mock_result = MagicMock()
        # Safety returns a list of lists
        mock_result.stdout = json.dumps([["requests", "<2.26.0", "2.25.0", "Security issue", "12345"]])

        with patch("subprocess.run", return_value=mock_result):
            result = run_safety(tmp_path, logger)

            assert len(result) == 1
            assert result[0].package == "requests"
            assert result[0].version == "2.25.0"

    def test_safety_empty_output(self, tmp_path, logger):
        """Test safety with empty output."""
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = run_safety(tmp_path, logger)

            assert result == []

    def test_safety_not_found(self, tmp_path, logger):
        """Test safety not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = run_safety(tmp_path, logger)

            assert result == []


class TestRunNpmAudit:
    """Tests for run_npm_audit function."""

    def test_npm_audit_success(self, tmp_path, logger):
        """Test successful npm audit run."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {
                "vulnerabilities": {
                    "lodash": {
                        "range": "<4.17.21",
                        "title": "Prototype Pollution",
                        "severity": "high",
                    }
                }
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            result = run_npm_audit(tmp_path, logger)

            assert len(result) == 1
            assert result[0].package == "lodash"
            assert result[0].severity == "high"

    def test_npm_audit_empty_output(self, tmp_path, logger):
        """Test npm audit with empty output."""
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = run_npm_audit(tmp_path, logger)

            assert result == []

    def test_npm_audit_not_found(self, tmp_path, logger):
        """Test npm not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = run_npm_audit(tmp_path, logger)

            assert result == []


class TestClassifyVulnSeverity:
    """Tests for classify_vuln_severity function."""

    def test_critical_from_aliases(self):
        """Test critical severity from aliases."""
        vuln = {"aliases": ["CVE-CRITICAL-123"]}
        assert classify_vuln_severity(vuln) == "critical"

    def test_critical_from_rce(self):
        """Test critical severity from RCE description."""
        vuln = {"description": "Remote code execution vulnerability"}
        assert classify_vuln_severity(vuln) == "critical"

    def test_critical_from_rce_short(self):
        """Test critical severity from RCE abbreviation."""
        vuln = {"description": "This allows RCE"}
        assert classify_vuln_severity(vuln) == "critical"

    def test_critical_from_sql_injection(self):
        """Test critical severity from SQL injection."""
        vuln = {"description": "SQL injection vulnerability"}
        assert classify_vuln_severity(vuln) == "critical"

    def test_critical_from_command_injection(self):
        """Test critical severity from command injection."""
        vuln = {"description": "Command injection possible"}
        assert classify_vuln_severity(vuln) == "critical"

    def test_default_high(self):
        """Test default high severity."""
        vuln = {"description": "Some other vulnerability"}
        assert classify_vuln_severity(vuln) == "high"

    def test_empty_vuln(self):
        """Test empty vulnerability dict."""
        vuln = {}
        assert classify_vuln_severity(vuln) == "high"


class TestCheckOutdatedPackages:
    """Tests for check_outdated_packages function."""

    def test_python_outdated(self, tmp_path, logger):
        """Test checking Python outdated packages."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps([{"name": "requests", "version": "2.25.0", "latest_version": "2.28.0"}])

        with patch("subprocess.run", return_value=mock_result):
            result = check_outdated_packages("python", tmp_path, logger)

            assert len(result) == 1

    def test_python_outdated_error(self, tmp_path, logger):
        """Test Python outdated check error handling."""
        with patch("subprocess.run", side_effect=Exception("pip error")):
            result = check_outdated_packages("python", tmp_path, logger)

            assert result == []

    def test_nodejs_outdated(self, tmp_path, logger):
        """Test checking Node.js outdated packages."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"lodash": {"current": "4.17.0", "latest": "4.17.21"}})

        with patch("subprocess.run", return_value=mock_result):
            result = check_outdated_packages("nodejs", tmp_path, logger)

            assert len(result) == 1
            assert result[0].name == "lodash"
            assert result[0].latest_version == "4.17.21"

    def test_nodejs_outdated_error(self, tmp_path, logger):
        """Test Node.js outdated check error handling."""
        with patch("subprocess.run", side_effect=Exception("npm error")):
            result = check_outdated_packages("nodejs", tmp_path, logger)

            assert result == []

    def test_unknown_project_type(self, tmp_path, logger):
        """Test unknown project type returns empty."""
        result = check_outdated_packages("unknown", tmp_path, logger)

        assert result == []
