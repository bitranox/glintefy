"""Common issue dataclasses for subservers.

Provides typed issue classes for consistent issue reporting across
all review subservers (deps, security, docs, perf, quality).
"""

from dataclasses import dataclass, asdict
from typing import Any, Literal

# Severity levels
SeverityType = Literal["critical", "warning", "info"]


@dataclass(slots=True)
class BaseIssue:
    """Base class for all issues.

    Attributes:
        type: Issue type identifier (e.g., "vulnerability", "outdated")
        severity: Issue severity level
        message: Human-readable description
    """

    type: str
    severity: SeverityType
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# --- Dependency Issues ---


@dataclass(slots=True)
class VulnerabilityIssue(BaseIssue):
    """Security vulnerability in a dependency.

    Attributes:
        package: Package name
        version: Affected version
        vuln_id: CVE or vulnerability ID
    """

    package: str = ""
    version: str = ""
    vuln_id: str = ""


@dataclass(slots=True)
class OutdatedIssue(BaseIssue):
    """Outdated package issue.

    Attributes:
        package: Package name
        version: Current version
        latest: Latest available version
    """

    package: str = ""
    version: str = ""
    latest: str = ""


@dataclass(slots=True)
class LicenseIssue(BaseIssue):
    """License compliance issue.

    Attributes:
        package: Package name
        license: License identifier
    """

    package: str = ""
    license: str = ""


@dataclass(slots=True)
class DependencyTree:
    """Dependency tree analysis results.

    Attributes:
        depth: Maximum dependency depth
        total: Total number of dependencies
        direct: Number of direct dependencies
    """

    depth: int = 0
    total: int = 0
    direct: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# --- Security Issues ---


@dataclass(slots=True)
class SecurityIssue(BaseIssue):
    """Security issue from static analysis.

    Attributes:
        file: Source file path
        line: Line number
        test_id: Test/rule identifier (e.g., B101)
        confidence: Confidence level
    """

    file: str = ""
    line: int = 0
    test_id: str = ""
    confidence: str = ""


# --- Documentation Issues ---


@dataclass(slots=True)
class DocstringIssue(BaseIssue):
    """Missing or inadequate docstring.

    Attributes:
        file: Source file path
        line: Line number
        name: Function/class/module name
        doc_type: Type of documentation issue
    """

    file: str = ""
    line: int = 0
    name: str = ""
    doc_type: str = ""


@dataclass(slots=True)
class ProjectDocIssue(BaseIssue):
    """Project documentation issue.

    Attributes:
        doc_file: Documentation file name
        required: Whether the doc is required
    """

    doc_file: str = ""
    required: bool = False


# --- Performance Issues ---


@dataclass(slots=True)
class PerformanceIssue(BaseIssue):
    """Performance-related issue.

    Attributes:
        file: Source file path
        line: Line number
        pattern: Pattern identifier
        impact: Estimated impact level
    """

    file: str = ""
    line: int = 0
    pattern: str = ""
    impact: str = ""


@dataclass(slots=True)
class HotspotIssue(BaseIssue):
    """Performance hotspot from profiling.

    Attributes:
        file: Source file path
        function: Function name
        time_percent: Percentage of total time
        calls: Number of calls
    """

    file: str = ""
    function: str = ""
    time_percent: float = 0.0
    calls: int = 0


# --- Metrics Dataclasses ---


@dataclass(slots=True)
class DepsMetrics:
    """Dependency analysis metrics.

    Attributes:
        project_type: Detected project type
        total_dependencies: Total dependency count
        direct_dependencies: Direct dependency count
        vulnerabilities_count: Number of vulnerabilities
        outdated_count: Number of outdated packages
        license_issues: Number of license issues
        critical_issues: Number of critical issues
        total_issues: Total issue count
    """

    project_type: str | None = None
    total_dependencies: int = 0
    direct_dependencies: int = 0
    vulnerabilities_count: int = 0
    outdated_count: int = 0
    license_issues: int = 0
    critical_issues: int = 0
    total_issues: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class SecurityMetrics:
    """Security analysis metrics.

    Attributes:
        files_scanned: Number of files scanned
        issues_found: Total issues found
        high_severity: High severity count
        medium_severity: Medium severity count
        low_severity: Low severity count
    """

    files_scanned: int = 0
    issues_found: int = 0
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class DocsMetrics:
    """Documentation analysis metrics.

    Attributes:
        files_analyzed: Number of files analyzed
        coverage_percent: Docstring coverage percentage
        missing_docstrings: Count of missing docstrings
        project_docs_found: Count of project docs found
        total_issues: Total issue count
    """

    files_analyzed: int = 0
    coverage_percent: float = 0.0
    missing_docstrings: int = 0
    project_docs_found: int = 0
    total_issues: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class PerfMetrics:
    """Performance analysis metrics.

    Attributes:
        files_analyzed: Number of files analyzed
        patterns_found: Number of expensive patterns found
        hotspots_found: Number of hotspots detected
        total_issues: Total issue count
    """

    files_analyzed: int = 0
    patterns_found: int = 0
    hotspots_found: int = 0
    total_issues: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# Helper to convert list of issues to dicts
def issues_to_dicts(issues: list[BaseIssue]) -> list[dict[str, Any]]:
    """Convert a list of issue dataclasses to dictionaries."""
    return [issue.to_dict() for issue in issues]
