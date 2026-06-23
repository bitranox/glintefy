"""Typed dataclasses for analyzer results.

All analyzers return typed dataclass instances instead of untyped dict[str, Any].
Conversion to dict happens only at JSON serialization boundaries.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from glintefy.subservers.common.issues import DocstringCoverageMetrics, TypeCoverageMetrics


# --- Complexity Analyzer Results ---


@dataclass(slots=True)
class CyclomaticComplexityItem:
    """Single function complexity result from radon cc."""

    file: str
    name: str
    type: str  # function/method/class
    complexity: int
    rank: str  # A, B, C, D, E, F
    line: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class MaintainabilityItem:
    """Single file maintainability result from radon mi."""

    file: str
    mi: float  # Maintainability Index
    rank: str  # A, B, C

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class CognitiveComplexityItem:
    """Single function cognitive complexity result."""

    file: str
    name: str
    line: int
    complexity: int
    exceeds_threshold: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class FunctionIssueItem:
    """Function-level issue (too long, too nested)."""

    file: str
    function: str
    line: int
    issue_type: str  # TOO_LONG, TOO_NESTED
    value: int
    threshold: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class ComplexityResults:
    """Results from ComplexityAnalyzer.analyze()."""

    complexity: list[CyclomaticComplexityItem] = field(default_factory=list)
    maintainability: list[MaintainabilityItem] = field(default_factory=list)
    cognitive: list[CognitiveComplexityItem] = field(default_factory=list)
    function_issues: list[FunctionIssueItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "complexity": [item.to_dict() for item in self.complexity],
            "maintainability": [item.to_dict() for item in self.maintainability],
            "cognitive": [item.to_dict() for item in self.cognitive],
            "function_issues": [item.to_dict() for item in self.function_issues],
        }


# --- Metrics Analyzer Results ---


@dataclass(slots=True)
class HalsteadItem:
    """Halstead metrics for a single file."""

    file: str
    h1: int = 0  # Distinct operators
    h2: int = 0  # Distinct operands
    N1: int = 0  # Total operators
    N2: int = 0  # Total operands
    vocabulary: int = 0
    length: int = 0
    volume: float = 0
    difficulty: float = 0
    effort: float = 0
    time: float = 0
    bugs: float = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class RawMetricsItem:
    """Raw metrics (LOC, SLOC, comments) for a single file."""

    file: str
    loc: int = 0  # Lines of code
    lloc: int = 0  # Logical lines of code
    sloc: int = 0  # Source lines of code
    comments: int = 0
    multi: int = 0  # Multi-line strings
    blank: int = 0
    single_comments: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class FileChurnInfo:
    """Churn info for a single file."""

    file: str
    commits: int = 0
    authors: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    total_changes: int = 0
    churn_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class CodeChurnResults:
    """Code churn analysis results."""

    files: list[FileChurnInfo] = field(default_factory=list)
    high_churn_files: list[FileChurnInfo] = field(default_factory=list)
    total_commits_analyzed: int = 0
    analysis_period_days: int = 90
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "files": [f.to_dict() for f in self.files],
            "high_churn_files": [f.to_dict() for f in self.high_churn_files],
            "total_commits_analyzed": self.total_commits_analyzed,
            "analysis_period_days": self.analysis_period_days,
        }
        if self.skip_reason:
            result["skip_reason"] = self.skip_reason
        return result


@dataclass(slots=True)
class MetricsResults:
    """Results from MetricsAnalyzer.analyze()."""

    halstead: list[HalsteadItem] = field(default_factory=list)
    raw_metrics: list[RawMetricsItem] = field(default_factory=list)
    code_churn: CodeChurnResults = field(default_factory=CodeChurnResults)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "halstead": [item.to_dict() for item in self.halstead],
            "raw_metrics": [item.to_dict() for item in self.raw_metrics],
            "code_churn": self.code_churn.to_dict(),
        }


# --- Static Analyzer Results ---


class RuffLocation(BaseModel):
    """Location within a file for a Ruff diagnostic."""

    model_config = ConfigDict(extra="ignore")

    row: int = 0
    column: int = 0


class RuffDiagnostic(BaseModel):
    """Single diagnostic from Ruff static analysis."""

    model_config = ConfigDict(extra="ignore")

    code: str = ""
    message: str = ""
    filename: str = ""
    location: RuffLocation = Field(default_factory=RuffLocation)
    url: str = ""
    noqa_row: int = 0


@dataclass(slots=True)
class RuffResults:
    """Ruff static analysis results."""

    ruff: str = ""  # Raw output
    ruff_json: list[RuffDiagnostic] = field(default_factory=list)  # Parsed diagnostics

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"ruff": self.ruff, "ruff_json": [d.model_dump() for d in self.ruff_json]}


@dataclass(slots=True)
class DuplicationResults:
    """Code duplication detection results."""

    duplicates: list[str] = field(default_factory=list)
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"duplicates": self.duplicates, "raw_output": self.raw_output}


@dataclass(slots=True)
class StaticResults:
    """Results from StaticAnalyzer.analyze()."""

    static: RuffResults = field(default_factory=RuffResults)
    duplication: DuplicationResults = field(default_factory=DuplicationResults)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "static": self.static.to_dict(),
            "duplication": self.duplication.to_dict(),
        }


# --- Test Analyzer Results ---


@dataclass(slots=True)
class SuiteIssueItem:
    """Single test suite issue (no assertions, long test, missing OS decorator)."""

    type: str  # NO_ASSERTIONS, LONG_TEST, MISSING_OS_DECORATOR
    file: str
    line: int
    message: str
    function: str | None = None
    os_checks: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "type": self.type,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }
        if self.function is not None:
            result["function"] = self.function
        if self.os_checks is not None:
            result["os_checks"] = self.os_checks
        return result


@dataclass(slots=True)
class SuiteFileInfo:
    """Test info for a single test file."""

    file: str
    test_count: int = 0
    assertion_count: int = 0
    issues: list[SuiteIssueItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "test_count": self.test_count,
            "assertion_count": self.assertion_count,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass(slots=True)
class SuiteCategories:
    """Test categorization counts."""

    unit: int = 0
    integration: int = 0
    e2e: int = 0
    unknown: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class SuiteResults:
    """Results from TestSuiteAnalyzer.analyze()."""

    test_files: list[SuiteFileInfo] = field(default_factory=list)
    total_tests: int = 0
    total_assertions: int = 0
    categories: SuiteCategories = field(default_factory=SuiteCategories)
    issues: list[SuiteIssueItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_files": [f.to_dict() for f in self.test_files],
            "total_tests": self.total_tests,
            "total_assertions": self.total_assertions,
            "categories": self.categories.to_dict(),
            "issues": [i.to_dict() for i in self.issues],
        }


# --- Architecture Analyzer Results ---


@dataclass(slots=True)
class GodObjectInfo:
    """God object detection info."""

    file: str
    class_name: str  # 'class' is reserved in Python
    line: int
    methods: int
    lines: int
    methods_threshold: int
    lines_threshold: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "class": self.class_name,
            "line": self.line,
            "methods": self.methods,
            "lines": self.lines,
            "methods_threshold": self.methods_threshold,
            "lines_threshold": self.lines_threshold,
        }


@dataclass(slots=True)
class HighCouplingInfo:
    """High coupling detection info."""

    file: str
    import_count: int
    threshold: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class ArchitectureMetrics:
    """Architecture analysis metrics."""

    god_objects: list[GodObjectInfo] = field(default_factory=list)
    highly_coupled: list[HighCouplingInfo] = field(default_factory=list)
    module_structure: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "god_objects": [g.to_dict() for g in self.god_objects],
            "highly_coupled": [h.to_dict() for h in self.highly_coupled],
            "module_structure": self.module_structure,
        }


@dataclass(slots=True)
class ImportCycleResults:
    """Import cycle detection results."""

    cycles: list[list[str]] = field(default_factory=list)
    import_graph: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"cycles": self.cycles, "import_graph": self.import_graph}


@dataclass(slots=True)
class RuntimeCheckInfo:
    """Runtime check detection info."""

    file: str
    function: str
    line: int
    check_count: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class ArchitectureResults:
    """Results from ArchitectureAnalyzer.analyze()."""

    architecture: ArchitectureMetrics = field(default_factory=ArchitectureMetrics)
    import_cycles: ImportCycleResults = field(default_factory=ImportCycleResults)
    runtime_checks: list[RuntimeCheckInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "architecture": self.architecture.to_dict(),
            "import_cycles": self.import_cycles.to_dict(),
            "runtime_checks": [r.to_dict() for r in self.runtime_checks],
        }


# --- Type Analyzer Results ---


@dataclass(slots=True)
class DeadCodeItem:
    """Dead code item from vulture."""

    file: str
    line: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class DeadCodeResults:
    """Dead code detection results."""

    dead_code: list[DeadCodeItem] = field(default_factory=list)
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dead_code": [d.to_dict() for d in self.dead_code],
            "raw_output": self.raw_output,
        }


@dataclass(slots=True)
class TypeResults:
    """Results from TypeAnalyzer.analyze()."""

    type_coverage: TypeCoverageMetrics = field(default_factory=TypeCoverageMetrics)
    dead_code: DeadCodeResults = field(default_factory=DeadCodeResults)
    docstring_coverage: DocstringCoverageMetrics = field(default_factory=DocstringCoverageMetrics)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type_coverage": self.type_coverage.model_dump(),
            "dead_code": self.dead_code.to_dict(),
            "docstring_coverage": self.docstring_coverage.model_dump(),
        }


# --- Combined Results ---


@dataclass(slots=True)
class QualityAnalysisResults:
    """Combined results from all quality analyzers.

    This is the main result type returned by the quality orchestrator.
    """

    # From ComplexityAnalyzer
    complexity: list[CyclomaticComplexityItem] = field(default_factory=list)
    maintainability: list[MaintainabilityItem] = field(default_factory=list)
    cognitive: list[CognitiveComplexityItem] = field(default_factory=list)
    function_issues: list[FunctionIssueItem] = field(default_factory=list)

    # From MetricsAnalyzer
    halstead: list[HalsteadItem] = field(default_factory=list)
    raw_metrics: list[RawMetricsItem] = field(default_factory=list)
    code_churn: CodeChurnResults = field(default_factory=CodeChurnResults)

    # From StaticAnalyzer
    static: RuffResults = field(default_factory=RuffResults)
    duplication: DuplicationResults = field(default_factory=DuplicationResults)

    # From TestSuiteAnalyzer
    tests: SuiteResults = field(default_factory=SuiteResults)

    # From ArchitectureAnalyzer
    architecture: ArchitectureMetrics = field(default_factory=ArchitectureMetrics)
    import_cycles: ImportCycleResults = field(default_factory=ImportCycleResults)
    runtime_checks: list[RuntimeCheckInfo] = field(default_factory=list)

    # From TypeAnalyzer
    type_coverage: TypeCoverageMetrics = field(default_factory=TypeCoverageMetrics)
    dead_code: DeadCodeResults = field(default_factory=DeadCodeResults)
    docstring_coverage: DocstringCoverageMetrics = field(default_factory=DocstringCoverageMetrics)

    # From JS analyzer (dict for now - external tool)
    js_analysis: dict[str, Any] = field(default_factory=dict)

    # From Beartype analyzer (dict for now - simple results)
    beartype: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "complexity": [item.to_dict() for item in self.complexity],
            "maintainability": [item.to_dict() for item in self.maintainability],
            "cognitive": [item.to_dict() for item in self.cognitive],
            "function_issues": [item.to_dict() for item in self.function_issues],
            "halstead": [item.to_dict() for item in self.halstead],
            "raw_metrics": [item.to_dict() for item in self.raw_metrics],
            "code_churn": self.code_churn.to_dict(),
            "static": self.static.to_dict(),
            "duplication": self.duplication.to_dict(),
            "tests": self.tests.to_dict(),
            "architecture": self.architecture.to_dict(),
            "import_cycles": self.import_cycles.to_dict(),
            "runtime_checks": [r.to_dict() for r in self.runtime_checks],
            "type_coverage": self.type_coverage.model_dump(),
            "dead_code": self.dead_code.to_dict(),
            "docstring_coverage": self.docstring_coverage.model_dump(),
            "js_analysis": self.js_analysis,
            "beartype": self.beartype,
        }
