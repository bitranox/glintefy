"""Tests for common issue dataclasses."""

from glintefy.subservers.common.issues import (
    BaseIssue,
    DependencyTree,
    DepsMetrics,
    DocstringIssue,
    DocsMetrics,
    HotspotIssue,
    LicenseIssue,
    OutdatedIssue,
    PerfMetrics,
    PerformanceIssue,
    ProjectDocIssue,
    SecurityIssue,
    SecurityMetrics,
    VulnerabilityIssue,
    issues_to_dicts,
)


class TestBaseIssue:
    """Tests for BaseIssue dataclass."""

    def test_creation(self):
        """Test basic issue creation."""
        issue = BaseIssue(type="test", severity="warning", message="Test message")

        assert issue.type == "test"
        assert issue.severity == "warning"
        assert issue.message == "Test message"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        issue = BaseIssue(type="test", severity="critical", message="Critical issue")
        result = issue.to_dict()

        assert isinstance(result, dict)
        assert result["type"] == "test"
        assert result["severity"] == "critical"
        assert result["message"] == "Critical issue"

    def test_slots(self):
        """Test that slots are used (no __dict__)."""
        issue = BaseIssue(type="test", severity="info", message="Info")
        assert not hasattr(issue, "__dict__")


class TestVulnerabilityIssue:
    """Tests for VulnerabilityIssue dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with default values."""
        issue = VulnerabilityIssue(
            type="vulnerability",
            severity="critical",
            message="CVE found",
        )

        assert issue.package == ""
        assert issue.version == ""
        assert issue.vuln_id == ""

    def test_creation_with_all_fields(self):
        """Test creation with all fields."""
        issue = VulnerabilityIssue(
            type="vulnerability",
            severity="critical",
            message="CVE-2023-1234 in requests",
            package="requests",
            version="2.25.0",
            vuln_id="CVE-2023-1234",
        )

        assert issue.package == "requests"
        assert issue.version == "2.25.0"
        assert issue.vuln_id == "CVE-2023-1234"

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes inherited and own fields."""
        issue = VulnerabilityIssue(
            type="vulnerability",
            severity="critical",
            message="Test",
            package="pkg",
            version="1.0",
            vuln_id="CVE-123",
        )
        result = issue.to_dict()

        assert "type" in result
        assert "severity" in result
        assert "message" in result
        assert "package" in result
        assert "version" in result
        assert "vuln_id" in result


class TestOutdatedIssue:
    """Tests for OutdatedIssue dataclass."""

    def test_creation(self):
        """Test outdated issue creation."""
        issue = OutdatedIssue(
            type="outdated",
            severity="warning",
            message="Package outdated",
            package="click",
            version="7.0.0",
            latest="8.1.0",
        )

        assert issue.package == "click"
        assert issue.version == "7.0.0"
        assert issue.latest == "8.1.0"


class TestLicenseIssue:
    """Tests for LicenseIssue dataclass."""

    def test_creation(self):
        """Test license issue creation."""
        issue = LicenseIssue(
            type="license",
            severity="critical",
            message="GPL license found",
            package="gpl-pkg",
            license="GPL-3.0",
        )

        assert issue.package == "gpl-pkg"
        assert issue.license == "GPL-3.0"


class TestDependencyTree:
    """Tests for DependencyTree dataclass."""

    def test_default_values(self):
        """Test default values."""
        tree = DependencyTree()

        assert tree.depth == 0
        assert tree.total == 0
        assert tree.direct == 0

    def test_custom_values(self):
        """Test custom values."""
        tree = DependencyTree(depth=3, total=50, direct=10)

        assert tree.depth == 3
        assert tree.total == 50
        assert tree.direct == 10

    def test_to_dict(self):
        """Test conversion to dictionary."""
        tree = DependencyTree(depth=2, total=25, direct=5)
        result = tree.to_dict()

        assert result == {"depth": 2, "total": 25, "direct": 5}


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""

    def test_creation(self):
        """Test security issue creation."""
        issue = SecurityIssue(
            type="hardcoded_password",
            severity="critical",
            message="Hardcoded password found",
            file="src/auth.py",
            line=42,
            test_id="B105",
            confidence="HIGH",
        )

        assert issue.file == "src/auth.py"
        assert issue.line == 42
        assert issue.test_id == "B105"
        assert issue.confidence == "HIGH"


class TestDocstringIssue:
    """Tests for DocstringIssue dataclass."""

    def test_creation(self):
        """Test docstring issue creation."""
        issue = DocstringIssue(
            type="missing_docstring",
            severity="warning",
            message="Function missing docstring",
            file="src/module.py",
            line=10,
            name="my_function",
            doc_type="function",
        )

        assert issue.file == "src/module.py"
        assert issue.line == 10
        assert issue.name == "my_function"
        assert issue.doc_type == "function"


class TestProjectDocIssue:
    """Tests for ProjectDocIssue dataclass."""

    def test_creation(self):
        """Test project doc issue creation."""
        issue = ProjectDocIssue(
            type="missing_readme",
            severity="critical",
            message="README not found",
            doc_file="README.md",
            required=True,
        )

        assert issue.doc_file == "README.md"
        assert issue.required is True


class TestPerformanceIssue:
    """Tests for PerformanceIssue dataclass."""

    def test_creation(self):
        """Test performance issue creation."""
        issue = PerformanceIssue(
            type="nested_loop",
            severity="warning",
            message="Nested loop detected",
            file="src/slow.py",
            line=25,
            pattern=r"for .+ in .+:\s*for .+ in .+:",
            impact="high",
        )

        assert issue.file == "src/slow.py"
        assert issue.line == 25
        assert issue.pattern == r"for .+ in .+:\s*for .+ in .+:"
        assert issue.impact == "high"


class TestHotspotIssue:
    """Tests for HotspotIssue dataclass."""

    def test_creation(self):
        """Test hotspot issue creation."""
        issue = HotspotIssue(
            type="slow_test",
            severity="critical",
            message="Slow test detected",
            file="tests/test_slow.py",
            function="test_heavy_computation",
            time_percent=45.5,
            calls=100,
        )

        assert issue.file == "tests/test_slow.py"
        assert issue.function == "test_heavy_computation"
        assert issue.time_percent == 45.5
        assert issue.calls == 100


class TestDepsMetrics:
    """Tests for DepsMetrics dataclass."""

    def test_default_values(self):
        """Test default values."""
        metrics = DepsMetrics()

        assert metrics.project_type is None
        assert metrics.total_dependencies == 0
        assert metrics.direct_dependencies == 0
        assert metrics.vulnerabilities_count == 0
        assert metrics.outdated_count == 0
        assert metrics.license_issues == 0
        assert metrics.critical_issues == 0
        assert metrics.total_issues == 0

    def test_custom_values(self):
        """Test custom values."""
        metrics = DepsMetrics(
            project_type="python",
            total_dependencies=50,
            direct_dependencies=10,
            vulnerabilities_count=2,
            outdated_count=5,
            license_issues=1,
            critical_issues=3,
            total_issues=8,
        )

        assert metrics.project_type == "python"
        assert metrics.total_dependencies == 50
        assert metrics.total_issues == 8

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = DepsMetrics(project_type="nodejs", total_issues=5)
        result = metrics.model_dump()

        assert result["project_type"] == "nodejs"
        assert result["total_issues"] == 5


class TestSecurityMetrics:
    """Tests for SecurityMetrics dataclass."""

    def test_creation(self):
        """Test security metrics creation."""
        metrics = SecurityMetrics(
            files_scanned=100,
            issues_found=15,
            high_severity=2,
            medium_severity=8,
            low_severity=5,
        )

        assert metrics.files_scanned == 100
        assert metrics.issues_found == 15
        assert metrics.high_severity == 2


class TestDocsMetrics:
    """Tests for DocsMetrics dataclass."""

    def test_creation(self):
        """Test docs metrics creation."""
        metrics = DocsMetrics(
            files_analyzed=50,
            coverage_percent=85.5,
            missing_docstrings=10,
            project_docs_found=3,
            total_issues=11,
        )

        assert metrics.files_analyzed == 50
        assert metrics.coverage_percent == 85.5
        assert metrics.missing_docstrings == 10


class TestPerfMetrics:
    """Tests for PerfMetrics dataclass."""

    def test_creation(self):
        """Test perf metrics creation."""
        metrics = PerfMetrics(
            files_analyzed=25,
            patterns_found=5,
            hotspots_found=2,
            total_issues=7,
        )

        assert metrics.files_analyzed == 25
        assert metrics.patterns_found == 5
        assert metrics.hotspots_found == 2


class TestIssuesToDicts:
    """Tests for issues_to_dicts helper function."""

    def test_empty_list(self):
        """Test with empty list."""
        result = issues_to_dicts([])
        assert result == []

    def test_single_issue(self):
        """Test with single issue."""
        issues = [BaseIssue(type="test", severity="warning", message="Test")]
        result = issues_to_dicts(issues)

        assert len(result) == 1
        assert result[0]["type"] == "test"

    def test_multiple_issues(self):
        """Test with multiple issues of different types."""
        issues = [
            VulnerabilityIssue(
                type="vulnerability",
                severity="critical",
                message="CVE found",
                package="pkg",
            ),
            OutdatedIssue(
                type="outdated",
                severity="warning",
                message="Outdated",
                package="pkg2",
            ),
        ]
        result = issues_to_dicts(issues)

        assert len(result) == 2
        assert result[0]["type"] == "vulnerability"
        assert result[0]["package"] == "pkg"
        assert result[1]["type"] == "outdated"
        assert result[1]["package"] == "pkg2"
