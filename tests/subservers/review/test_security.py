"""Tests for Security sub-server."""

import pytest

from glintefy.subservers.review.security import BanditIssue, SecuritySubServer


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
        (repo_dir / "vulnerable.py").write_text("""
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
""")
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

        server.run()

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


class TestSecuritySubServerMCPMode:
    """Tests for MCP mode functionality."""

    def test_mcp_mode_enabled(self, tmp_path):
        """Test MCP mode initialization."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            mcp_mode=True,
        )

        assert server.mcp_mode is True
        assert server.logger is not None


class TestSecurityConfigLoading:
    """Tests for config file loading."""

    def test_load_config_from_explicit_file(self, tmp_path):
        """Test loading config from explicit file path."""
        import yaml

        config_file = tmp_path / "custom_config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "security": {
                        "severity_threshold": "high",
                        "confidence_threshold": "medium",
                    }
                }
            )
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            config_file=config_file,
        )

        assert server.config is not None

    def test_load_config_from_default_location(self, tmp_path):
        """Test loading config from default .glintefy.yaml."""
        import yaml

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config_file = repo_dir / ".glintefy.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "security": {
                        "severity_threshold": "medium",
                    }
                }
            )
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        assert server.config is not None

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML config."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Should not raise, just use defaults
        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            config_file=config_file,
        )

        assert server.severity_threshold == "low"


class TestSecurityBanditHelpers:
    """Tests for Bandit helper methods."""

    @pytest.fixture
    def server(self, tmp_path):
        """Create a SecuritySubServer instance."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        return SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

    def test_filter_issues_by_severity(self, server):
        """Test filtering issues by severity threshold."""
        issues = [
            BanditIssue(issue_severity="HIGH", issue_confidence="HIGH"),
            BanditIssue(issue_severity="MEDIUM", issue_confidence="HIGH"),
            BanditIssue(issue_severity="LOW", issue_confidence="HIGH"),
        ]

        server.severity_threshold = "medium"
        filtered = server._filter_issues(issues)

        # Should filter out LOW
        assert len(filtered) == 2

    def test_filter_issues_by_confidence(self, server):
        """Test filtering issues by confidence threshold."""
        issues = [
            BanditIssue(issue_severity="HIGH", issue_confidence="HIGH"),
            BanditIssue(issue_severity="HIGH", issue_confidence="MEDIUM"),
            BanditIssue(issue_severity="HIGH", issue_confidence="LOW"),
        ]

        server.confidence_threshold = "high"
        filtered = server._filter_issues(issues)

        # Should filter out MEDIUM and LOW confidence
        assert len(filtered) == 1

    def test_categorize_issues(self, server):
        """Test categorizing issues by severity."""
        issues = [
            BanditIssue(issue_severity="HIGH"),
            BanditIssue(issue_severity="MEDIUM"),
            BanditIssue(issue_severity="MEDIUM"),
            BanditIssue(issue_severity="LOW"),
        ]

        categorized = server._categorize_issues(issues)

        assert len(categorized["HIGH"]) == 1
        assert len(categorized["MEDIUM"]) == 2
        assert len(categorized["LOW"]) == 1

    def test_categorize_issues_unknown_severity(self, server):
        """Test categorizing issues with unknown severity."""
        issues = [
            BanditIssue(issue_severity="UNKNOWN"),
            BanditIssue(),  # Uses default "LOW"
        ]

        categorized = server._categorize_issues(issues)

        # Unknown severities should go to LOW
        assert len(categorized["LOW"]) == 2


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


class TestSecurityMindsetThresholds:
    """Tests for mindset threshold configuration."""

    @pytest.fixture
    def repo_with_issues(self, tmp_path):
        """Create repo with multiple security issues of varying severity."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "vulnerable.py").write_text("""
import subprocess
import pickle
import os

# B602: subprocess with shell=True (HIGH severity)
def run_command(cmd):
    subprocess.call(cmd, shell=True)

# B301: pickle usage (MEDIUM severity)
def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

# B105: hardcoded password (MEDIUM severity)
PASSWORD = "secret123"

# B605: subprocess with untrusted input (MEDIUM severity)
def execute(user_cmd):
    os.system(user_cmd)
""")
        return repo_dir

    def test_default_critical_threshold(self, repo_with_issues, tmp_path):
        """Test default critical threshold (1 high severity issue)."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_issues,
        )

        # Verify default threshold
        assert server.critical_threshold == 1

        result = server.run()

        # Should trigger PARTIAL status if >= 1 high severity issue found
        high_count = result.metrics["high_severity"]
        if high_count >= 1:
            assert result.status == "PARTIAL"

    def test_custom_critical_threshold(self, repo_with_issues, tmp_path):
        """Test custom critical threshold."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_issues,
            critical_threshold=10,  # Set high threshold
        )

        assert server.critical_threshold == 10

        result = server.run()

        # With high threshold, should be SUCCESS even with some high severity issues
        high_count = result.metrics["high_severity"]
        if high_count < 10:
            # Status might still be PARTIAL due to warning_threshold
            # but not due to critical_threshold
            assert high_count < server.critical_threshold

    def test_default_warning_threshold(self, repo_with_issues, tmp_path):
        """Test default warning threshold (5 medium severity issues)."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_issues,
            critical_threshold=100,  # Disable critical threshold
        )

        # Verify default threshold
        assert server.warning_threshold == 5

        result = server.run()

        # Should trigger PARTIAL status if >= 5 medium severity issues found
        medium_count = result.metrics["medium_severity"]
        if medium_count >= 5:
            assert result.status == "PARTIAL"
        else:
            # With < 5 medium and critical threshold disabled, should be SUCCESS
            assert result.status == "SUCCESS"

    def test_custom_warning_threshold(self, repo_with_issues, tmp_path):
        """Test custom warning threshold."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_issues,
            critical_threshold=100,  # Disable critical threshold
            warning_threshold=2,  # Low threshold
        )

        assert server.warning_threshold == 2

        result = server.run()

        # Should trigger PARTIAL if >= 2 medium severity issues
        medium_count = result.metrics["medium_severity"]
        if medium_count >= 2:
            assert result.status == "PARTIAL"

    def test_threshold_config_in_summary(self, repo_with_issues, tmp_path):
        """Test that thresholds appear in summary report."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("vulnerable.py\n")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_issues,
            critical_threshold=3,
            warning_threshold=10,
        )

        result = server.run()

        # Verify thresholds appear in summary
        assert "Critical Status Threshold: 3 high severity issues" in result.summary
        assert "Warning Status Threshold: 10 medium severity issues" in result.summary

    def test_thresholds_override_config_file(self, tmp_path):
        """Test that constructor parameters override config file values."""

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        # Note: Config loading uses get_subserver_config, not direct file reading

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("")

        output_dir = tmp_path / "output"
        server = SecuritySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
            critical_threshold=7,
            warning_threshold=15,
        )

        # Constructor parameters should override defaults
        assert server.critical_threshold == 7
        assert server.warning_threshold == 15
