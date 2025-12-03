"""Cache analysis summary generation.

Generates markdown summary reports for cache analysis results.
"""

from dataclasses import dataclass


@dataclass
class SummaryConfig:
    """Configuration for summary generation."""

    cache_size: int = 128
    hit_rate_threshold: float = 20.0
    speedup_threshold: float = 5.0


def generate_summary(
    pure: list,
    candidates: list,
    screening: list,
    validation: list,
    existing_evals: list,
    config: SummaryConfig,
    profile_warnings: list[str] | None = None,
) -> str:
    """Generate markdown summary for cache analysis.

    Args:
        pure: List of pure function results
        candidates: List of cache candidates
        screening: List of batch screening results
        validation: List of individual validation results
        existing_evals: List of existing cache evaluations
        config: Summary configuration
        profile_warnings: Optional profile data warnings

    Returns:
        Markdown formatted summary
    """
    profile_warnings = profile_warnings or []
    recommendations = [r for r in validation if r.recommendation == "APPLY"]
    used_production_data = any(e.hits > 0 or e.misses > 0 for e in existing_evals)

    lines = ["# Cache Analysis Report", ""]

    lines.extend(_format_profile_warnings(profile_warnings))
    lines.extend(_format_analysis_method(used_production_data))
    lines.extend(_format_overview(pure, candidates, screening, validation, recommendations, existing_evals))
    lines.extend(_format_existing_cache_evaluation(existing_evals))
    lines.extend(_format_new_recommendations(recommendations, config, existing_evals))

    return "\n".join(lines)


def _format_profile_warnings(warnings: list[str]) -> list[str]:
    """Format profile data warnings section."""
    if not warnings:
        return []

    lines = ["## [WARN] Profile Data Warnings", ""]
    for warning in warnings:
        lines.append(f"> {warning}")
        lines.append(">")
    lines.append("")
    return lines


def _format_analysis_method(used_production_data: bool) -> list[str]:
    """Format analysis method section."""
    lines = ["## Analysis Method", ""]

    if used_production_data:
        lines.extend(
            [
                "[PASS] **Using Production Cache Data**",
                "",
                "Recommendations based on real cache statistics from your application.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "[WARN]  **Using Static Code Analysis**",
                "",
                "No production profiling data available. Recommendations based on static code analysis.",
                "",
                "### [TIP] Get More Accurate Results with Profiling Data",
                "",
                "Profile your application with a single command:",
                "",
                "```bash",
                "# Profile any command",
                "python -m glintefy review profile -- python my_app.py",
                "python -m glintefy review profile -- pytest tests/",
                "python -m glintefy review profile -- python -m my_module",
                "",
                "# Then analyze caches",
                "python -m glintefy review cache",
                "```",
                "",
                "[REF] **Full examples:** See glintefy's `docs/HOW_TO_PROFILE.md`",
                "",
            ]
        )

    return lines


def _format_overview(
    pure: list,
    candidates: list,
    screening: list,
    validation: list,
    recommendations: list,
    existing_evals: list,
) -> list[str]:
    """Format overview section."""
    pure_count = len([c for c in pure if c.is_pure])
    screening_passed = len([r for r in screening if r.passed_screening]) if screening else 0
    screening_total = len(screening) if screening else 0

    return [
        "## Overview",
        "",
        f"- Pure functions identified: {pure_count}",
        f"- Cache candidates (pure + hot): {len(candidates)}",
        f"- Batch screening passed: {screening_passed}/{screening_total}",
        f"- Individual validation: {len(validation)} tested",
        f"- **New cache recommendations: {len(recommendations)}**",
        f"- **Existing caches evaluated: {len(existing_evals)}**",
        "",
    ]


def _format_existing_cache_evaluation(existing_evals: list) -> list[str]:
    """Format existing cache evaluation section."""
    if not existing_evals:
        return []

    keep_caches = [e for e in existing_evals if e.recommendation == "KEEP"]
    remove_caches = [e for e in existing_evals if e.recommendation == "REMOVE"]
    adjust_caches = [e for e in existing_evals if e.recommendation == "ADJUST_SIZE"]

    lines = [
        "## Existing Cache Evaluation",
        "",
        f"- **Keep:** {len(keep_caches)} caches performing well",
        f"- **Remove:** {len(remove_caches)} caches with low hit rates",
        f"- **Adjust:** {len(adjust_caches)} caches with suboptimal maxsize",
        "",
    ]

    lines.extend(_format_remove_caches(remove_caches))
    lines.extend(_format_adjust_caches(adjust_caches))
    lines.extend(_format_keep_caches(keep_caches))

    return lines


def _format_remove_caches(remove_caches: list) -> list[str]:
    """Format caches to remove section."""
    if not remove_caches:
        return []

    lines = ["### Remove (Low Hit Rate)", ""]
    for eval_result in remove_caches:
        c = eval_result.candidate
        maxsize_str = c.current_maxsize if c.current_maxsize >= 0 else "unbounded"
        lines.extend(
            [
                f"#### `{c.function_name}` ({c.file_path.name}:{c.line_number})",
                f"- **Current:** `@lru_cache(maxsize={maxsize_str})`",
                f"- **Hit rate:** {eval_result.hit_rate:.1f}%",
                f"- **Recommendation:** {eval_result.reason}",
                "",
            ]
        )
    return lines


def _format_adjust_caches(adjust_caches: list) -> list[str]:
    """Format caches to adjust section."""
    if not adjust_caches:
        return []

    lines = ["### Adjust Size", ""]
    for eval_result in adjust_caches:
        c = eval_result.candidate
        maxsize_str = c.current_maxsize if c.current_maxsize >= 0 else "unbounded"
        lines.extend(
            [
                f"#### `{c.function_name}` ({c.file_path.name}:{c.line_number})",
                f"- **Current:** `@lru_cache(maxsize={maxsize_str})`",
                f"- **Suggested:** `@lru_cache(maxsize={eval_result.suggested_maxsize})`",
                f"- **Hit rate:** {eval_result.hit_rate:.1f}%",
                f"- **Reason:** {eval_result.reason}",
                "",
            ]
        )
    return lines


def _format_keep_caches(keep_caches: list) -> list[str]:
    """Format caches to keep section."""
    if not keep_caches:
        return []

    lines = ["### Keep (Performing Well)", ""]
    for eval_result in keep_caches:
        c = eval_result.candidate
        lines.append(f"- `{c.function_name}` ({c.file_path.name}:{c.line_number}): {eval_result.hit_rate:.1f}% hit rate")
    lines.append("")
    return lines


def _format_new_recommendations(
    recommendations: list,
    config: SummaryConfig,
    existing_evals: list,
) -> list[str]:
    """Format new cache recommendations section."""
    if recommendations:
        lines = ["## Recommended New Caching", ""]
        for result in recommendations:
            c = result.candidate
            lines.extend(
                [
                    f"### `{c.function_name}` ({c.file_path.name}:{c.line_number})",
                    f"- **Module:** `{c.module_path}`",
                    f"- **Expected speedup:** {result.speedup_percent:.1f}%",
                    f"- **Cache hit rate:** {result.hit_rate:.1f}%",
                    f"- **Decorator:** `@lru_cache(maxsize={config.cache_size})`",
                    f"- **Evidence:** {result.hits} hits, {result.misses} misses in test suite",
                    "",
                ]
            )
        return lines

    if not existing_evals:
        return [
            "## No Recommendations",
            "",
            "No functions met both criteria:",
            f"- Cache hit rate >= {config.hit_rate_threshold}%",
            f"- Performance speedup >= {config.speedup_threshold}%",
            "",
        ]

    return []


def generate_issues(validation: list, existing_evals: list, cache_size: int) -> list[dict]:
    """Convert cache analysis results to issues for the report.

    Args:
        validation: Individual validation results
        existing_evals: Existing cache evaluations
        cache_size: Cache maxsize for recommendations

    Returns:
        List of issue dictionaries
    """
    issues = []

    issues.extend(_generate_recommendation_issues(validation, cache_size))
    issues.extend(_generate_remove_cache_issues(existing_evals))
    issues.extend(_generate_adjust_cache_issues(existing_evals))

    return issues


def _generate_recommendation_issues(validation: list, cache_size: int) -> list[dict]:
    """Generate issues for new cache recommendations."""
    issues = []
    recommendations = [r for r in validation if r.recommendation == "APPLY"]

    for result in recommendations:
        c = result.candidate
        issues.append(
            {
                "type": "cache_opportunity",
                "severity": "info",
                "message": (f"Cache opportunity: {c.function_name} - {result.speedup_percent:.1f}% speedup, {result.hit_rate:.1f}% hit rate"),
                "file": str(c.file_path),
                "line": c.line_number,
                "function": c.function_name,
                "speedup_percent": round(result.speedup_percent, 2),
                "hit_rate": round(result.hit_rate, 2),
                "recommended_decorator": f"@lru_cache(maxsize={cache_size})",
            }
        )

    return issues


def _generate_remove_cache_issues(existing_evals: list) -> list[dict]:
    """Generate issues for caches that should be removed."""
    issues = []
    remove_evals = [e for e in existing_evals if e.recommendation == "REMOVE"]

    for eval_result in remove_evals:
        c = eval_result.candidate
        issues.append(
            {
                "type": "ineffective_cache",
                "severity": "warning",
                "message": (f"Ineffective cache: {c.function_name} - {eval_result.hit_rate:.1f}% hit rate (remove @lru_cache)"),
                "file": str(c.file_path),
                "line": c.line_number,
                "function": c.function_name,
                "hit_rate": round(eval_result.hit_rate, 2),
                "reason": eval_result.reason,
            }
        )

    return issues


def _generate_adjust_cache_issues(existing_evals: list) -> list[dict]:
    """Generate issues for caches that need size adjustment."""
    issues = []
    adjust_evals = [e for e in existing_evals if e.recommendation == "ADJUST_SIZE"]

    for eval_result in adjust_evals:
        c = eval_result.candidate
        current_size = c.current_maxsize if c.current_maxsize >= 0 else "unbounded"
        direction = "reduce" if eval_result.suggested_maxsize < c.current_maxsize else "increase"

        issues.append(
            {
                "type": "cache_size_adjustment",
                "severity": "info",
                "message": (f"Cache size adjustment: {c.function_name} - {direction} maxsize from {current_size} to {eval_result.suggested_maxsize}"),
                "file": str(c.file_path),
                "line": c.line_number,
                "function": c.function_name,
                "current_maxsize": current_size,
                "suggested_maxsize": eval_result.suggested_maxsize,
                "hit_rate": round(eval_result.hit_rate, 2),
                "reason": eval_result.reason,
            }
        )

    return issues
