"""Tests for Deps sub-server."""

import pytest

from glintefy.subservers.review.deps import DepsSubServer
from glintefy.subservers.review.deps_scanners import OutdatedPackage, Vulnerability


class TestDepsSubServer:
    """Tests for DepsSubServer class."""

    @pytest.fixture
    def python_project(self, tmp_path):
        """Create a Python project with pyproject.toml."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create pyproject.toml
        (project_dir / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "0.1.0"
dependencies = [
    "requests>=2.28.0",
    "click>=8.0.0",
]
""")

        return project_dir

    @pytest.fixture
    def npm_project(self, tmp_path):
        """Create a Node.js project with package.json."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create package.json
        (project_dir / "package.json").write_text("""
{
    "name": "test-project",
    "version": "1.0.0",
    "dependencies": {
        "express": "^4.18.0"
    }
}
""")

        return project_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        output_dir = tmp_path / "output"
        server = DepsSubServer(output_dir=output_dir, repo_path=tmp_path)

        assert server.name == "deps"
        assert server.output_dir == output_dir
        assert server.repo_path == tmp_path
        assert server.scan_vulnerabilities is True
        assert server.check_licenses is True
        assert server.check_outdated is True

    def test_initialization_custom_options(self, tmp_path):
        """Test initialization with custom options."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            scan_vulnerabilities=False,
            check_licenses=False,
            check_outdated=False,
        )

        assert server.scan_vulnerabilities is False
        assert server.check_licenses is False
        assert server.check_outdated is False

    def test_validate_inputs_no_deps(self, tmp_path):
        """Test validation fails with no dependency files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=empty_dir,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No dependency files" in m for m in missing)

    def test_validate_inputs_with_pyproject(self, python_project, tmp_path):
        """Test validation passes with pyproject.toml."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=python_project,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_validate_inputs_with_package_json(self, npm_project, tmp_path):
        """Test validation passes with package.json."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=npm_project,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_detect_project_type_python(self, python_project, tmp_path):
        """Test detection of Python project."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=python_project,
        )

        project_type = server._detect_project_type()

        assert project_type == "python"

    def test_detect_project_type_nodejs(self, npm_project, tmp_path):
        """Test detection of Node.js project."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=npm_project,
        )

        project_type = server._detect_project_type()

        assert project_type == "nodejs"

    def test_detect_project_type_none(self, tmp_path):
        """Test detection returns None for unknown project."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=empty_dir,
        )

        project_type = server._detect_project_type()

        assert project_type is None

    def test_execute_no_deps(self, tmp_path):
        """Test execution with no dependency files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=empty_dir,
        )

        result = server.run()

        # Should fail validation when no dependency files exist
        assert result.status == "FAILED"
        assert "No dependency files" in result.summary or "validation" in result.summary.lower()

    def test_execute_python_project(self, python_project, tmp_path):
        """Test execution on Python project."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=python_project,
        )

        result = server.run()

        # Should complete (may not find vulnerabilities in test env)
        assert result.status in ("SUCCESS", "PARTIAL", "FAILED")
        assert result.metrics.get("project_type") == "python"

    def test_mindset_loaded(self, tmp_path):
        """Test that deps mindset is loaded."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        assert server.mindset is not None
        assert server.mindset.name == "deps"
        assert "auditor" in server.mindset.role.lower() or "deps" in server.mindset.role.lower()

    def test_summary_includes_mindset(self, python_project, tmp_path):
        """Test that summary includes mindset information."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=python_project,
        )

        result = server.run()

        assert "Reviewer Mindset" in result.summary
        assert "Verdict" in result.summary

    def test_license_classification(self, tmp_path):
        """Test license classification."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        # Permissive licenses should be allowed
        assert "MIT" in server.PERMISSIVE_LICENSES
        assert "Apache-2.0" in server.PERMISSIVE_LICENSES

        # Copyleft licenses should be tracked
        assert "GPL-3.0" in server.COPYLEFT_LICENSES

    def test_vulnerability_to_issues(self, tmp_path):
        """Test conversion of vulnerabilities to issues."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        vulns = [
            Vulnerability(
                package="test-pkg",
                version="1.0.0",
                vulnerability_id="CVE-2023-1234",
                description="Test vulnerability",
                severity="high",
            )
        ]

        issues = server._vulnerabilities_to_issues(vulns)

        assert len(issues) == 1
        assert issues[0].type == "vulnerability"
        assert issues[0].severity == "critical"
        assert "test-pkg" in issues[0].message

    def test_outdated_to_issues(self, tmp_path):
        """Test conversion of outdated packages to issues."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        outdated = [
            OutdatedPackage(
                name="requests",
                version="2.25.0",
                latest_version="2.31.0",
            )
        ]

        issues = server._outdated_to_issues(outdated)

        assert len(issues) == 1
        assert issues[0].type == "outdated"
        assert issues[0].severity == "warning"
        assert "requests" in issues[0].message

    def test_licenses_to_issues_disallowed(self, tmp_path):
        """Test license issues for disallowed licenses."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            disallowed_licenses=["GPL-3.0"],
        )

        licenses = [
            {"Name": "gpl-pkg", "License": "GPL-3.0"},
        ]

        issues = server._licenses_to_issues(licenses)

        assert len(issues) == 1
        assert issues[0].type == "license"
        assert issues[0].severity == "critical"


class TestDepsSubServerMCPMode:
    """Tests for DepsSubServer in MCP mode."""

    def test_mcp_mode_enabled(self, tmp_path):
        """Test that MCP mode can be enabled."""
        server = DepsSubServer(
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            mcp_mode=True,
        )

        assert server.mcp_mode is True
        # Logger should be configured for stderr in MCP mode
        assert server.logger is not None
