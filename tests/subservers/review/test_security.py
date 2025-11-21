"""Tests for Security sub-server."""

from pathlib import Path

import pytest

from btx_fix_mcp.subservers.review.security import SecuritySubServer


class TestSecuritySubServer:
    """Tests for SecuritySubServer class."""

    @pytest.fixture
    def scope_output(self, tmp_path):
        """Create mock scope output directory."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("main.py\n")
        return scope_dir

    @pytest.fixture
    def repo_with_secure_code(self, tmp_path):
        """Create repo with secure Python code."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text('''
"""Safe module."""

def greet(name: str) -> str:
    """Greet a person safely."""
    return f"Hello, {name}!"
''')
        return repo_dir

    @pytest.fixture
    def repo_with_vulnerable_code(self, tmp_path):
        """Create repo with vulnerable Python code."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "vulnerable.py").write_text('''
import subprocess
import pickle

# B602: subprocess with shell=True
def run_command(cmd):
    subprocess.call(cmd, shell=True)

# B301: pickle usage
def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

# B105: hardcoded password
PASSWORD = "secret123"
''')
        return repo_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        assert server.name == "security"
        assert server.severity_threshold == "low"
        assert server.confidence_threshold == "low"

    def test_initialization_custom_thresholds(self, tmp_path):
        """Test initialization with custom thresholds."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            severity_threshold="high",
            confidence_threshold="medium",
        )

        assert server.severity_threshold == "high"
        assert server.confidence_threshold == "medium"

    def test_validate_inputs_missing_files(self, tmp_path):
        """Test validation fails without files list."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No files list" in m for m in missing)

    def test_validate_inputs_invalid_threshold(self, scope_output, tmp_path):
        """Test validation fails with invalid threshold."""
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=scope_output,
            output_dir=output_dir,
        )
        server.severity_threshold = "invalid"

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("Invalid severity_threshold" in m for m in missing)

    def test_validate_inputs_success(self, scope_output, tmp_path):
        """Test validation succeeds with valid inputs."""
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=scope_output,
            output_dir=output_dir,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_execute_no_python_files(self, tmp_path):
        """Test execution with no Python files."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_to_review.txt").write_text("README.md\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["files_scanned"] == 0

    def test_execute_with_secure_code(self, repo_with_secure_code, tmp_path):
        """Test execution with secure code."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("main.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_secure_code,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["files_scanned"] == 1
        assert result.metrics["issues_found"] == 0

    def test_execute_with_vulnerable_code(self, repo_with_vulnerable_code, tmp_path):
        """Test execution with vulnerable code."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_vulnerable_code,
        )

        result = server.run()

        # Should find issues
        assert result.metrics["files_scanned"] == 1
        assert result.metrics["issues_found"] > 0

    def test_severity_filtering(self, repo_with_vulnerable_code, tmp_path):
        """Test filtering by severity threshold."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        # With high threshold - should filter out lower severity
        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_vulnerable_code,
            severity_threshold="high",
        )

        result = server.run()

        # High threshold should filter more issues
        high_only = result.metrics["issues_found"]

        # With low threshold - should include all
        output_dir2 = tmp_path / "output2"
        server2 = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir2,
            repo_path=repo_with_vulnerable_code,
            severity_threshold="low",
        )

        result2 = server2.run()

        # Low threshold should include more issues
        assert result2.metrics["issues_found"] >= high_only

    def test_artifacts_created(self, repo_with_secure_code, tmp_path):
        """Test that artifact files are created."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("main.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_secure_code,
        )

        result = server.run()

        assert "bandit_full" in result.artifacts
        assert result.artifacts["bandit_full"].exists()
        assert "security_issues" in result.artifacts
        assert result.artifacts["security_issues"].exists()

    def test_summary_format(self, repo_with_secure_code, tmp_path):
        """Test summary is properly formatted."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("main.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_secure_code,
        )

        result = server.run()

        assert result.summary.startswith("# Security Analysis Report")
        assert "## Overview" in result.summary
        assert "Files Scanned" in result.summary
        assert "Issues by Severity" in result.summary

    def test_integration_protocol_compliance(self, repo_with_secure_code, tmp_path):
        """Test integration protocol compliance."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("main.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_secure_code,
        )

        result = server.run()

        assert (output_dir / "status.txt").exists()
        assert (output_dir / "security_summary.md").exists()

    def test_config_from_parameters(self, tmp_path):
        """Test configuration via constructor parameters."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_to_review.txt").write_text("")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
            severity_threshold="high",
            confidence_threshold="medium",
        )

        assert server.severity_threshold == "high"
        assert server.confidence_threshold == "medium"


class TestSecuritySubServerIntegration:
    """Integration tests with actual Bandit analysis."""

    def test_full_scan_workflow(self, tmp_path):
        """Test complete security scan workflow."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "app.py").write_text('''
"""Application module."""

import hashlib

def hash_password(password: str) -> str:
    """Hash password securely."""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_input(user_input: str) -> bool:
    """Validate user input."""
    return len(user_input) < 100 and user_input.isalnum()
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("app.py\n")

        output_dir = tmp_path / "security"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        result = server.run()

        assert result.status in ("SUCCESS", "PARTIAL")
        assert result.metrics["files_scanned"] == 1
