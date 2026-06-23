"""Issue compilation for Quality sub-server.

Extracts issue compilation logic to reduce __init__ complexity.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .analyzer_results import QualityAnalysisResults
from .config import QualityConfig

# Severity levels for issues
SeverityType = Literal["error", "warning", "info"]


@dataclass(slots=True)
class Issue:
    """Base class for all quality issues.

    Attributes:
        type: Issue type identifier (e.g., "high_complexity", "god_object")
        severity: Issue severity level
        message: Human-readable description
        file: Source file path (optional)
        line: Line number (optional)
    """

    type: str
    severity: SeverityType
    message: str
    file: str = ""
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass(slots=True)
class ThresholdIssue(Issue):
    """Issue with a measured value and threshold.

    Used for complexity, maintainability, coverage violations.
    """

    value: int | float | str = 0
    threshold: int | float = 0
    name: str = ""


@dataclass(slots=True)
class RuleIssue(Issue):
    """Issue from a linter rule violation.

    Used for Ruff, ESLint issues.
    """

    rule: str = ""


def compile_all_issues(
    results: QualityAnalysisResults,
    config: QualityConfig,
    repo_path: Path,
) -> list[Issue]:
    """Compile all issues from various analyses.

    Args:
        results: Typed analysis results from orchestrator
        config: Quality configuration with thresholds
        repo_path: Repository path for relative paths

    Returns:
        List of Issue dataclass instances (convert with to_dict() at serialization)
    """
    issues: list[Issue] = []
    t = config.thresholds

    # Complexity issues
    _add_complexity_issues(issues, results, t.complexity, t.complexity_error)

    # Maintainability issues
    _add_maintainability_issues(issues, results, t.maintainability, t.maintainability_error)

    # Function issues
    _add_function_issues(issues, results)

    # Cognitive complexity issues
    _add_cognitive_issues(issues, results, t.cognitive_complexity)

    # Test issues
    _add_test_issues(issues, results)

    # Architecture issues
    _add_architecture_issues(issues, results, t.coupling_threshold)

    # Runtime check issues
    _add_runtime_check_issues(issues, results)

    # Static analysis (Ruff) issues
    _add_ruff_issues(issues, results, repo_path)

    # Duplication issues
    _add_duplication_issues(issues, results)

    # Coverage issues
    _add_coverage_issues(issues, results, t.min_type_coverage, t.min_docstring_coverage)

    # Import cycle issues
    _add_import_cycle_issues(issues, results)

    # Dead code issues
    _add_dead_code_issues(issues, results)

    # Code churn issues
    _add_churn_issues(issues, results)

    # JS/TS issues
    _add_js_issues(issues, results)

    # Beartype issues
    _add_beartype_issues(issues, results)

    return issues


def _add_complexity_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    threshold: int,
    error_threshold: int,
) -> None:
    """Add cyclomatic complexity issues."""
    for r in results.complexity:
        if r.complexity > threshold:
            issues.append(
                ThresholdIssue(
                    type="high_complexity",
                    severity="warning" if r.complexity <= error_threshold else "error",
                    file=r.file,
                    line=r.line,
                    name=r.name,
                    value=r.complexity,
                    threshold=threshold,
                    message=f"Function '{r.name}' has complexity {r.complexity} (threshold: {threshold})",
                )
            )


def _add_maintainability_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    threshold: int,
    error_threshold: int,
) -> None:
    """Add maintainability index issues."""
    for r in results.maintainability:
        if r.mi < threshold:
            issues.append(
                ThresholdIssue(
                    type="low_maintainability",
                    severity="warning" if r.mi >= error_threshold else "error",
                    file=r.file,
                    value=r.mi,
                    threshold=threshold,
                    message=f"File has maintainability index {r.mi:.1f} (threshold: {threshold})",
                )
            )


def _add_function_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add function length/nesting issues."""
    for fi in results.function_issues:
        issues.append(
            ThresholdIssue(
                type=fi.issue_type.lower(),
                severity="error" if fi.value > fi.threshold * 2 else "warning",
                file=fi.file,
                line=fi.line,
                name=fi.function,
                value=fi.value,
                threshold=fi.threshold,
                message=fi.message,
            )
        )


def _add_cognitive_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    threshold: int,
) -> None:
    """Add cognitive complexity issues."""
    for r in results.cognitive:
        if r.exceeds_threshold:
            issues.append(
                ThresholdIssue(
                    type="high_cognitive_complexity",
                    severity="warning",
                    file=r.file,
                    line=r.line,
                    name=r.name,
                    value=r.complexity,
                    threshold=threshold,
                    message=f"Function '{r.name}' has cognitive complexity {r.complexity} (threshold: {threshold})",
                )
            )


def _add_test_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add test-related issues."""
    for ti in results.tests.issues:
        issues.append(
            Issue(
                type=ti.type.lower(),
                severity="warning",
                file=ti.file,
                line=ti.line,
                message=ti.message,
            )
        )


def _add_architecture_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    coupling_threshold: int,
) -> None:
    """Add architecture issues (god objects, coupling)."""
    for obj in results.architecture.god_objects:
        issues.append(
            ThresholdIssue(
                type="god_object",
                severity="error",
                file=obj.file,
                line=obj.line,
                name=obj.class_name,
                value=f"{obj.methods} methods, {obj.lines} lines",
                message=f"Class '{obj.class_name}' is a god object ({obj.methods} methods, {obj.lines} lines)",
            )
        )

    for item in results.architecture.highly_coupled:
        issues.append(
            ThresholdIssue(
                type="high_coupling",
                severity="warning",
                file=item.file,
                value=item.import_count,
                threshold=item.threshold,
                message=f"Module has {item.import_count} imports (threshold: {item.threshold})",
            )
        )


def _add_runtime_check_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add runtime check optimization issues."""
    for rc in results.runtime_checks:
        issues.append(
            ThresholdIssue(
                type="runtime_check_optimization",
                severity="info",
                file=rc.file,
                line=rc.line,
                name=rc.function,
                value=rc.check_count,
                message=rc.message,
            )
        )


def _add_ruff_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    repo_path: Path,
) -> None:
    """Add Ruff static analysis issues."""
    for ruff_issue in results.static.ruff_json:
        file_path = ruff_issue.filename
        try:
            rel_path = str(Path(file_path).relative_to(repo_path)) if file_path else ""
        except ValueError:
            rel_path = file_path
        issues.append(
            RuleIssue(
                type=f"ruff_{ruff_issue.code or 'unknown'}",
                severity="warning",
                file=rel_path,
                line=ruff_issue.location.row,
                message=ruff_issue.message,
                rule=ruff_issue.code,
            )
        )


def _add_duplication_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add code duplication issues."""
    for dup in results.duplication.duplicates:
        issues.append(
            Issue(
                type="code_duplication",
                severity="warning",
                message=dup,
            )
        )


def _add_coverage_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
    min_type_coverage: int,
    min_docstring_coverage: int,
) -> None:
    """Add type and docstring coverage issues."""
    type_coverage_percent = results.type_coverage.coverage_percent
    if type_coverage_percent < min_type_coverage:
        issues.append(
            ThresholdIssue(
                type="low_type_coverage",
                severity="warning",
                value=type_coverage_percent,
                threshold=min_type_coverage,
                message=f"Type coverage is {type_coverage_percent}% (minimum: {min_type_coverage}%)",
            )
        )

    docstring_coverage_percent = results.docstring_coverage.coverage_percent
    if docstring_coverage_percent < min_docstring_coverage:
        issues.append(
            ThresholdIssue(
                type="low_docstring_coverage",
                severity="warning",
                value=docstring_coverage_percent,
                threshold=min_docstring_coverage,
                message=f"Docstring coverage is {docstring_coverage_percent}% (minimum: {min_docstring_coverage}%)",
            )
        )


def _add_import_cycle_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add import cycle issues."""
    for cycle in results.import_cycles.cycles:
        issues.append(
            ThresholdIssue(
                type="import_cycle",
                severity="error",
                value=" -> ".join(cycle),
                message=f"Import cycle detected: {' -> '.join(cycle)}",
            )
        )


def _add_dead_code_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add dead code issues."""
    for dc in results.dead_code.dead_code:
        issues.append(
            ThresholdIssue(
                type="dead_code",
                severity="warning",
                file=dc.file,
                line=dc.line,
                value=0,  # DeadCodeItem doesn't have confidence
                message=dc.message,
            )
        )


def _add_churn_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add high churn file issues."""
    analysis_period = results.code_churn.analysis_period_days
    for cf in results.code_churn.high_churn_files:
        issues.append(
            ThresholdIssue(
                type="high_churn",
                severity="warning",
                file=cf.file,
                value=f"{cf.commits} commits, {cf.authors} authors",
                message=f"High churn file: {cf.file} ({cf.commits} commits by {cf.authors} authors in {analysis_period} days)",
            )
        )


def _add_js_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add JavaScript/TypeScript issues."""
    for js_issue in results.js_analysis.get("issues", []):
        issues.append(
            RuleIssue(
                type=f"eslint_{js_issue.get('rule', 'unknown')}",
                severity=js_issue.get("severity", "warning"),
                file=js_issue["file"],
                line=js_issue["line"],
                message=js_issue["message"],
                rule=js_issue.get("rule", ""),
            )
        )


def _add_beartype_issues(
    issues: list[Issue],
    results: QualityAnalysisResults,
) -> None:
    """Add beartype runtime type check issues."""
    if not results.beartype.get("passed", True):
        for err in results.beartype.get("errors", []):
            issues.append(
                Issue(
                    type="runtime_type_error",
                    severity="error",
                    message=err,
                )
            )
