"""Common issue dataclasses for subservers.

Provides typed issue classes for consistent issue reporting across
all review subservers (deps, security, docs, perf, quality).
"""

from dataclasses import asdict, dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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
        value: Numeric value for sorting (e.g., nesting depth, complexity score)
    """

    file: str = ""
    line: int = 0
    pattern: str = ""
    impact: str = ""
    value: int = 0


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


# --- Coverage Metrics (Pydantic) ---


class TypeCoverageMetrics(BaseModel):
    """Type coverage analysis metrics.

    Attributes:
        coverage_percent: Percentage of typed functions
        typed_functions: Count of typed functions
        untyped_functions: Count of untyped functions
        errors: List of type checking errors
        raw_output: Raw mypy output
    """

    model_config = ConfigDict(extra="forbid")

    coverage_percent: int = 0
    typed_functions: int = 0
    untyped_functions: int = 0
    errors: list[str] = Field(default_factory=list)
    raw_output: str = ""


class DocstringCoverageMetrics(BaseModel):
    """Docstring coverage analysis metrics.

    Attributes:
        coverage_percent: Percentage of documented functions/classes
        missing: List of items missing docstrings
        raw_output: Raw interrogate output
    """

    model_config = ConfigDict(extra="forbid")

    coverage_percent: float = 0.0
    missing: list[str] = Field(default_factory=list)
    raw_output: str = ""


# --- Metrics Dataclasses (Pydantic) ---


class DepsMetrics(BaseModel):
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

    model_config = ConfigDict(extra="forbid")

    project_type: str | None = None
    total_dependencies: int = 0
    direct_dependencies: int = 0
    vulnerabilities_count: int = 0
    outdated_count: int = 0
    license_issues: int = 0
    critical_issues: int = 0
    total_issues: int = 0


class SecurityMetrics(BaseModel):
    """Security analysis metrics.

    Attributes:
        files_scanned: Number of files scanned
        issues_found: Total issues found
        high_severity: High severity count
        medium_severity: Medium severity count
        low_severity: Low severity count
    """

    model_config = ConfigDict(extra="forbid")

    files_scanned: int = 0
    issues_found: int = 0
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0


class DocsMetrics(BaseModel):
    """Documentation analysis metrics.

    Attributes:
        files_analyzed: Number of files analyzed
        coverage_percent: Docstring coverage percentage
        missing_docstrings: Count of missing docstrings
        project_docs_found: Count of project docs found
        total_issues: Total issue count
    """

    model_config = ConfigDict(extra="forbid")

    files_analyzed: int = 0
    coverage_percent: float = 0.0
    missing_docstrings: int = 0
    project_docs_found: int = 0
    total_issues: int = 0


class PerfMetrics(BaseModel):
    """Performance analysis metrics.

    Attributes:
        files_analyzed: Number of files analyzed
        patterns_found: Number of expensive patterns found
        hotspots_found: Number of hotspots detected
        total_issues: Total issue count
    """

    model_config = ConfigDict(extra="forbid")

    files_analyzed: int = 0
    patterns_found: int = 0
    hotspots_found: int = 0
    total_issues: int = 0


class ScopeMetrics(BaseModel):
    """Scope analysis metrics.

    Attributes:
        total_files: Total files found
        code_files: Code files count
        test_files: Test files count
        doc_files: Documentation files count
        config_files: Configuration files count
        mode: Analysis mode (git, full, etc.)
    """

    model_config = ConfigDict(extra="forbid")

    total_files: int = 0
    code_files: int = 0
    test_files: int = 0
    doc_files: int = 0
    config_files: int = 0
    mode: str = "git"


class QualityMetrics(BaseModel):
    """Quality analysis metrics.

    Attributes:
        files_analyzed: Total files analyzed
        python_files: Python files count
        js_files: JavaScript/TypeScript files count
        total_functions: Total functions analyzed
        high_complexity_count: Functions with complexity > threshold
        high_cognitive_count: Functions with high cognitive complexity
        low_mi_count: Files with low maintainability index
        functions_too_long: Functions exceeding length threshold
        functions_too_nested: Functions exceeding nesting depth
        god_objects: Classes exceeding size/method thresholds
        highly_coupled_modules: Modules with high coupling
        import_cycles: Number of import cycles detected
        duplicate_blocks: Code duplication blocks
        dead_code_items: Unused code items (vars, functions, imports)
        docstring_coverage_percent: Percentage of code with docstrings
        type_coverage_percent: Percentage of code with type hints
        test_coverage_percent: Test coverage percentage
        high_churn_files: Files with high modification frequency
        beartype_passed: Beartype runtime checks passed
        critical_issues: Critical severity issues
        warning_issues: Warning severity issues
        total_issues: Total issues found
    """

    model_config = ConfigDict(extra="forbid")

    files_analyzed: int = 0
    python_files: int = 0
    js_files: int = 0
    total_functions: int = 0
    high_complexity_count: int = 0
    high_cognitive_count: int = 0
    low_mi_count: int = 0
    functions_too_long: int = 0
    functions_too_nested: int = 0
    god_objects: int = 0
    highly_coupled_modules: int = 0
    import_cycles: int = 0
    duplicate_blocks: int = 0
    dead_code_items: int = 0
    docstring_coverage_percent: float = 0.0
    type_coverage_percent: float = 0.0
    test_coverage_percent: float = 0.0
    high_churn_files: int = 0
    beartype_passed: bool = True
    critical_issues: int = 0
    warning_issues: int = 0
    total_issues: int = 0


# Helper to convert list of issues to dicts
def issues_to_dicts(issues: list[BaseIssue]) -> list[dict[str, Any]]:
    """Convert a list of issue dataclasses to dictionaries."""
    return [issue.to_dict() for issue in issues]
