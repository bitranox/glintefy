"""Summary generation for Quality sub-server.

Extracts summary generation logic to reduce __init__ complexity.
"""

from glintefy.subservers.common.issues import (
    DocstringCoverageMetrics,
    QualityMetrics,
    TypeCoverageMetrics,
)
from glintefy.subservers.common.mindsets import (
    AnalysisVerdict,
    ReviewerMindset,
    evaluate_results,
)

from .analyzer_results import QualityAnalysisResults, SuiteResults
from .config import QualityConfig, QualityThresholds
from .issues import Issue


def generate_comprehensive_summary(
    metrics: QualityMetrics,
    results: QualityAnalysisResults,
    all_issues: list[Issue],
    mindset: ReviewerMindset,
    config: QualityConfig,
) -> str:
    """Generate comprehensive markdown summary with mindset evaluation.

    Args:
        metrics: Quality metrics dataclass
        results: Typed analysis results
        all_issues: List of Issue dataclass instances
        mindset: Reviewer mindset for evaluation
        config: Quality configuration

    Returns:
        Markdown formatted summary string
    """
    t = config.thresholds

    # Calculate raw totals from typed raw_metrics
    total_loc = sum(r.loc for r in results.raw_metrics)
    total_sloc = sum(r.sloc for r in results.raw_metrics)
    total_comments = sum(r.comments for r in results.raw_metrics)

    # Evaluate results with mindset
    critical_issues = [i for i in all_issues if i.severity == "error"]
    warning_issues = [i for i in all_issues if i.severity == "warning"]
    total_items = metrics.files_analyzed or 1

    verdict = evaluate_results(mindset, critical_issues, warning_issues, total_items)

    lines = _build_header_section(mindset, verdict)
    lines.extend(_build_overview_section(metrics))
    lines.extend(_build_code_metrics_section(total_loc, total_sloc, total_comments))
    lines.extend(_build_quality_issues_section(metrics, t))
    lines.extend(_build_coverage_section(results.type_coverage, results.docstring_coverage, t))
    lines.extend(_build_test_section(results.tests, metrics))
    lines.extend(_build_critical_issues_section(critical_issues))
    lines.extend(_build_recommendations_section(metrics, results.type_coverage, results.docstring_coverage, t))
    lines.extend(_build_approval_section(verdict))

    return "\n".join(lines)


def _build_header_section(mindset: ReviewerMindset, verdict: AnalysisVerdict) -> list[str]:
    """Build header and verdict section."""
    return [
        "# Quality Analysis Report",
        "",
        "## Reviewer Mindset",
        "",
        mindset.format_header(),
        "",
        mindset.format_approach(),
        "",
        "## Verdict",
        "",
        f"**{verdict.verdict_text}**",
        "",
        f"- Critical issues: {verdict.critical_count} ({verdict.critical_ratio:.1f}%)",
        f"- Warnings: {verdict.warning_count} ({verdict.warning_ratio:.1f}%)",
        f"- Total items analyzed: {verdict.total_items}",
        "",
    ]


def _build_overview_section(metrics: QualityMetrics) -> list[str]:
    """Build overview section."""
    return [
        "## Overview",
        "",
        f"**Files Analyzed**: {metrics.files_analyzed} ({metrics.python_files} Python, {metrics.js_files} JS/TS)",
        f"**Functions Analyzed**: {metrics.total_functions}",
        f"**Total Issues Found**: {metrics.total_issues}",
        f"**Critical Issues**: {metrics.critical_issues}",
        "",
    ]


def _build_code_metrics_section(total_loc: int, total_sloc: int, total_comments: int) -> list[str]:
    """Build code metrics section."""
    comment_ratio = round(total_comments / total_sloc * 100, 1) if total_sloc > 0 else 0
    return [
        "## Code Metrics",
        "",
        f"- Total LOC: **{total_loc:,}**",
        f"- Source LOC (SLOC): **{total_sloc:,}**",
        f"- Comments: **{total_comments:,}**",
        f"- Comment Ratio: **{comment_ratio}%**",
        "",
    ]


def _build_quality_issues_section(metrics: QualityMetrics, t: QualityThresholds) -> list[str]:
    """Build quality issues summary section."""
    return [
        "## Quality Issues Summary",
        "",
        f"- Functions >50 lines: **{metrics.functions_too_long}**",
        f"- High cyclomatic complexity (>{t.complexity}): **{metrics.high_complexity_count}**",
        f"- High cognitive complexity (>{t.cognitive_complexity}): **{metrics.high_cognitive_count}**",
        f"- Functions with nesting >{t.max_nesting_depth}: **{metrics.functions_too_nested}**",
        f"- Code duplication blocks: **{metrics.duplicate_blocks}**",
        f"- God objects: **{metrics.god_objects}**",
        f"- Highly coupled modules: **{metrics.highly_coupled_modules}**",
        f"- Import cycles: **{metrics.import_cycles}**",
        f"- Dead code items: **{metrics.dead_code_items}**",
        "",
    ]


def _build_coverage_section(
    type_cov: TypeCoverageMetrics,
    doc_cov: DocstringCoverageMetrics,
    t: QualityThresholds,
) -> list[str]:
    """Build coverage metrics section."""
    return [
        "## Coverage Metrics",
        "",
        f"- Type coverage: **{type_cov.coverage_percent}%** (minimum: {t.min_type_coverage}%)",
        f"- Docstring coverage: **{doc_cov.coverage_percent}%** (minimum: {t.min_docstring_coverage}%)",
        "",
    ]


def _build_test_section(tests: SuiteResults, metrics: QualityMetrics) -> list[str]:
    """Build test suite analysis section."""
    assertions_per_test = round(tests.total_assertions / tests.total_tests, 1) if tests.total_tests > 0 else 0

    return [
        "## Test Suite Analysis",
        "",
        f"- Total tests: **{tests.total_tests}**",
        f"- Total assertions: **{tests.total_assertions}**",
        f"- Assertions per test: **{assertions_per_test}**",
        f"- Unit tests: {tests.categories.unit}",
        f"- Integration tests: {tests.categories.integration}",
        f"- E2E tests: {tests.categories.e2e}",
        f"- Test issues: **{len(tests.issues)}**",
        "",
        "## Runtime Type Checking (Beartype)",
        "",
        f"- Status: **{'[PASS] Passed' if metrics.beartype_passed else '[FAIL] Failed'}**",
        "",
    ]


def _build_critical_issues_section(critical_issues: list[Issue]) -> list[str]:
    """Build critical issues section."""
    if not critical_issues:
        return []

    lines = ["## Critical Issues (Must Fix)", ""]
    for issue in critical_issues[:15]:
        file_info = f"`{issue.file}`" if issue.file else ""
        lines.append(f"- [HIGH] {file_info}: {issue.message}")
    if len(critical_issues) > 15:
        lines.append(f"- ... and {len(critical_issues) - 15} more critical issues")
    lines.append("")
    return lines


def _build_recommendations_section(
    metrics: QualityMetrics,
    type_cov: TypeCoverageMetrics,
    doc_cov: DocstringCoverageMetrics,
    t: QualityThresholds,
) -> list[str]:
    """Build refactoring recommendations section."""
    lines = ["## Refactoring Recommendations", ""]
    rec_num = 1

    recommendations = [
        (metrics.functions_too_long > 0, f"**Break Down Long Functions**: {metrics.functions_too_long} functions exceed 50 lines"),
        (metrics.high_complexity_count > 0, f"**Reduce Cyclomatic Complexity**: {metrics.high_complexity_count} functions exceed threshold"),
        (metrics.high_cognitive_count > 0, f"**Reduce Cognitive Complexity**: {metrics.high_cognitive_count} functions are too complex"),
        (metrics.duplicate_blocks > 0, f"**Extract Duplicated Code**: {metrics.duplicate_blocks} duplicate blocks found"),
        (metrics.god_objects > 0, f"**Refactor God Objects**: {metrics.god_objects} classes need decomposition"),
        (metrics.import_cycles > 0, f"**Break Import Cycles**: {metrics.import_cycles} cycles detected"),
        (type_cov.coverage_percent < t.min_type_coverage, f"**Add Type Annotations**: Coverage is {type_cov.coverage_percent}%"),
        (doc_cov.coverage_percent < t.min_docstring_coverage, f"**Add Docstrings**: Coverage is {doc_cov.coverage_percent}%"),
        (metrics.dead_code_items > 0, f"**Remove Dead Code**: {metrics.dead_code_items} unused items found"),
        (metrics.high_churn_files > 0, f"**Review High Churn Files**: {metrics.high_churn_files} files with frequent changes"),
    ]

    for condition, text in recommendations:
        if condition:
            lines.append(f"{rec_num}. {text}")
            rec_num += 1

    if metrics.total_issues == 0:
        lines.append("[PASS] No quality issues detected!")

    return lines


def _build_approval_section(verdict: AnalysisVerdict) -> list[str]:
    """Build approval status section."""
    lines = ["", "## Approval Status", "", f"**{verdict.verdict_text}**"]
    if verdict.recommendations:
        lines.append("")
        for rec in verdict.recommendations:
            lines.append(f"- {rec}")
    return lines
