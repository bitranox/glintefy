"""Issue compilation for Quality sub-server.

Extracts issue compilation logic to reduce __init__ complexity.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Literal

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
    results: dict[str, Any],
    config: QualityConfig,
    repo_path: Path,
) -> list[dict[str, Any]]:
    """Compile all issues from various analyses.

    Args:
        results: Analysis results dictionary
        config: Quality configuration with thresholds
        repo_path: Repository path for relative paths

    Returns:
        List of issue dictionaries
    """
    issues: list[dict[str, Any]] = []
    t = config.thresholds

    # Complexity issues
    _add_complexity_issues(issues, results, t.complexity)

    # Maintainability issues
    _add_maintainability_issues(issues, results, t.maintainability)

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
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    threshold: int,
) -> None:
    """Add cyclomatic complexity issues."""
    for r in results.get("complexity", []):
        if r.get("complexity", 0) > threshold:
            issue = ThresholdIssue(
                type="high_complexity",
                severity="warning" if r["complexity"] <= 20 else "error",
                file=r["file"],
                line=r.get("line", 0),
                name=r["name"],
                value=r["complexity"],
                threshold=threshold,
                message=f"Function '{r['name']}' has complexity {r['complexity']} (threshold: {threshold})",
            )
            issues.append(issue.to_dict())


def _add_maintainability_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    threshold: int,
) -> None:
    """Add maintainability index issues."""
    for r in results.get("maintainability", []):
        if r.get("mi", 100) < threshold:
            issue = ThresholdIssue(
                type="low_maintainability",
                severity="warning" if r["mi"] >= 10 else "error",
                file=r["file"],
                value=r["mi"],
                threshold=threshold,
                message=f"File has maintainability index {r['mi']:.1f} (threshold: {threshold})",
            )
            issues.append(issue.to_dict())


def _add_function_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add function length/nesting issues."""
    for raw_issue in results.get("function_issues", []):
        issue = ThresholdIssue(
            type=raw_issue["issue_type"].lower(),
            severity="error" if raw_issue["value"] > raw_issue["threshold"] * 2 else "warning",
            file=raw_issue["file"],
            line=raw_issue["line"],
            name=raw_issue["function"],
            value=raw_issue["value"],
            threshold=raw_issue["threshold"],
            message=raw_issue["message"],
        )
        issues.append(issue.to_dict())


def _add_cognitive_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    threshold: int,
) -> None:
    """Add cognitive complexity issues."""
    for r in results.get("cognitive", []):
        if r.get("exceeds_threshold"):
            func_name = r.get("function", r.get("name", "unknown"))
            complexity_value = r.get("complexity", 0)
            issue = ThresholdIssue(
                type="high_cognitive_complexity",
                severity="warning",
                file=r.get("file", ""),
                line=r.get("line", 0),
                name=func_name,
                value=complexity_value,
                threshold=threshold,
                message=f"Function '{func_name}' has cognitive complexity {complexity_value} (threshold: {threshold})",
            )
            issues.append(issue.to_dict())


def _add_test_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add test-related issues."""
    for test_issue in results.get("tests", {}).get("issues", []):
        issue_type = test_issue.get("type", "test_issue").lower()
        issue = Issue(
            type=issue_type,
            severity="warning",
            file=test_issue.get("file", ""),
            line=test_issue.get("line", 0),
            message=test_issue.get("message", ""),
        )
        issues.append(issue.to_dict())


def _add_architecture_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    coupling_threshold: int,
) -> None:
    """Add architecture issues (god objects, coupling)."""
    arch = results.get("architecture", {})

    for obj in arch.get("god_objects", []):
        issue = ThresholdIssue(
            type="god_object",
            severity="error",
            file=obj["file"],
            line=obj["line"],
            name=obj["class"],
            value=f"{obj['methods']} methods, {obj['lines']} lines",
            message=f"Class '{obj['class']}' is a god object ({obj['methods']} methods, {obj['lines']} lines)",
        )
        issues.append(issue.to_dict())

    for item in arch.get("highly_coupled", []):
        threshold = item.get("threshold", coupling_threshold)
        issue = ThresholdIssue(
            type="high_coupling",
            severity="warning",
            file=item["file"],
            value=item["import_count"],
            threshold=threshold,
            message=f"Module has {item['import_count']} imports (threshold: {threshold})",
        )
        issues.append(issue.to_dict())


def _add_runtime_check_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add runtime check optimization issues."""
    for rc in results.get("runtime_checks", []):
        issue = ThresholdIssue(
            type="runtime_check_optimization",
            severity="info",
            file=rc["file"],
            line=rc["line"],
            name=rc["function"],
            value=rc["check_count"],
            message=rc["message"],
        )
        issues.append(issue.to_dict())


def _add_ruff_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    repo_path: Path,
) -> None:
    """Add Ruff static analysis issues."""
    for ruff_issue in results.get("static", {}).get("ruff_json", []):
        file_path = ruff_issue.get("filename", "")
        try:
            rel_path = str(Path(file_path).relative_to(repo_path)) if file_path else ""
        except ValueError:
            rel_path = file_path
        issue = RuleIssue(
            type=f"ruff_{ruff_issue.get('code', 'unknown')}",
            severity="warning",
            file=rel_path,
            line=ruff_issue.get("location", {}).get("row", 0),
            message=ruff_issue.get("message", ""),
            rule=ruff_issue.get("code", ""),
        )
        issues.append(issue.to_dict())


def _add_duplication_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add code duplication issues."""
    for dup in results.get("duplication", {}).get("duplicates", []):
        issue = Issue(
            type="code_duplication",
            severity="warning",
            message=dup,
        )
        issues.append(issue.to_dict())


def _add_coverage_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
    min_type_coverage: int,
    min_docstring_coverage: int,
) -> None:
    """Add type and docstring coverage issues."""
    type_cov = results.get("type_coverage", {})
    if type_cov.get("coverage_percent", 100) < min_type_coverage:
        issue = ThresholdIssue(
            type="low_type_coverage",
            severity="warning",
            value=type_cov["coverage_percent"],
            threshold=min_type_coverage,
            message=f"Type coverage is {type_cov['coverage_percent']}% (minimum: {min_type_coverage}%)",
        )
        issues.append(issue.to_dict())

    doc_cov = results.get("docstring_coverage", {})
    if doc_cov.get("coverage_percent", 100) < min_docstring_coverage:
        issue = ThresholdIssue(
            type="low_docstring_coverage",
            severity="warning",
            value=doc_cov["coverage_percent"],
            threshold=min_docstring_coverage,
            message=f"Docstring coverage is {doc_cov['coverage_percent']}% (minimum: {min_docstring_coverage}%)",
        )
        issues.append(issue.to_dict())


def _add_import_cycle_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add import cycle issues."""
    for cycle in results.get("import_cycles", {}).get("cycles", []):
        issue = ThresholdIssue(
            type="import_cycle",
            severity="error",
            value=" -> ".join(cycle),
            message=f"Import cycle detected: {' -> '.join(cycle)}",
        )
        issues.append(issue.to_dict())


def _add_dead_code_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add dead code issues."""
    for dc in results.get("dead_code", {}).get("dead_code", []):
        issue = ThresholdIssue(
            type="dead_code",
            severity="warning",
            file=dc["file"],
            line=dc["line"],
            value=dc.get("confidence", 0),
            message=dc["message"],
        )
        issues.append(issue.to_dict())


def _add_churn_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add high churn file issues."""
    for churn_file in results.get("code_churn", {}).get("high_churn_files", []):
        issue = ThresholdIssue(
            type="high_churn",
            severity="warning",
            file=churn_file["file"],
            value=f"{churn_file['commits']} commits, {churn_file['authors']} authors",
            message=f"High churn file: {churn_file['file']} ({churn_file['commits']} commits by {churn_file['authors']} authors in 90 days)",
        )
        issues.append(issue.to_dict())


def _add_js_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add JavaScript/TypeScript issues."""
    for js_issue in results.get("js_analysis", {}).get("issues", []):
        issue = RuleIssue(
            type=f"eslint_{js_issue.get('rule', 'unknown')}",
            severity=js_issue.get("severity", "warning"),
            file=js_issue["file"],
            line=js_issue["line"],
            message=js_issue["message"],
            rule=js_issue.get("rule", ""),
        )
        issues.append(issue.to_dict())


def _add_beartype_issues(
    issues: list[dict[str, Any]],
    results: dict[str, Any],
) -> None:
    """Add beartype runtime type check issues."""
    if not results.get("beartype", {}).get("passed", True):
        for err in results.get("beartype", {}).get("errors", []):
            issue = Issue(
                type="runtime_type_error",
                severity="error",
                message=err,
            )
            issues.append(issue.to_dict())
