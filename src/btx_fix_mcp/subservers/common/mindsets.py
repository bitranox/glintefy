"""Reviewer mindsets for code analysis.

This module provides reviewer personas that define the approach, questions,
and judgment criteria for different types of code review.

Mindsets are loaded from configuration and used to:
1. Format tool descriptions for MCP servers
2. Evaluate analysis results and render verdicts
3. Generate reviewer-style summaries in reports
"""

from dataclasses import dataclass, field
from typing import Any

from btx_fix_mcp.config import get_config


@dataclass
class JudgmentCriteria:
    """Criteria for judging analysis results."""

    critical_threshold: float = 10.0  # % of critical issues to reject
    warning_threshold: float = 25.0  # % of warnings for needs_work
    verdict_pass: str = "✅ APPROVED"
    verdict_warning: str = "⚠️ APPROVED WITH COMMENTS"
    verdict_needs_work: str = "🔧 NEEDS WORK"
    verdict_reject: str = "❌ REJECTED"


@dataclass
class ReviewerMindset:
    """A reviewer persona with approach, questions, and judgment criteria."""

    name: str
    role: str
    traits: list[str] = field(default_factory=list)
    approach: dict[str, str] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)
    judgment: JudgmentCriteria = field(default_factory=JudgmentCriteria)

    def format_header(self) -> str:
        """Format mindset as a header for reports."""
        traits_str = ", ".join(self.traits)
        return f"**You are a {self.role}** - {traits_str}."

    def format_approach(self) -> str:
        """Format approach as bullet points."""
        lines = ["**Your approach:**"]
        for key, value in self.approach.items():
            # Convert key from snake_case to Title Case
            label = key.replace("_", " ").title()
            lines.append(f"- ✓ **{label}:** {value}")
        return "\n".join(lines)

    def format_questions(self) -> str:
        """Format questions as bullet points."""
        lines = ["**Your Questions:**"]
        for question in self.questions:
            lines.append(f'- "{question}"')
        return "\n".join(lines)

    def format_full(self) -> str:
        """Format complete mindset description."""
        return "\n\n".join(
            [
                self.format_header(),
                self.format_approach(),
                self.format_questions(),
            ]
        )

    def format_for_tool_description(self) -> str:
        """Format mindset for MCP tool description (concise)."""
        traits_str = ", ".join(self.traits)
        approach_items = [f"- {v}" for v in list(self.approach.values())[:3]]
        approach_str = "\n".join(approach_items)

        return f"""Review with {self.role} mindset ({traits_str}).

APPROACH:
{approach_str}

QUESTIONS TO ASK:
- {self.questions[0] if self.questions else "Is this correct?"}
- {self.questions[1] if len(self.questions) > 1 else "Let me verify."}"""


def get_mindset(name: str, config: dict | None = None) -> ReviewerMindset:
    """Load a reviewer mindset from configuration.

    Args:
        name: Mindset name (e.g., "quality", "security", "docs", "perf")
        config: Optional config dict (loaded from defaultconfig.toml if not provided)

    Returns:
        ReviewerMindset instance
    """
    if config is None:
        config = get_config()

    # Navigate to mindsets section
    mindsets_config = config.get("review", {}).get("mindsets", {}).get(name, {})

    if not mindsets_config:
        # Return default mindset
        return ReviewerMindset(
            name=name,
            role=f"{name} reviewer",
            traits=["thorough", "precise"],
            approach={"verify": "Verify all claims with evidence"},
            questions=["Is this correct? Let me check."],
        )

    # Extract judgment criteria
    judgment_config = mindsets_config.get("judgment", {})
    judgment = JudgmentCriteria(
        critical_threshold=judgment_config.get("critical_threshold", 10.0),
        warning_threshold=judgment_config.get("warning_threshold", 25.0),
        verdict_pass=judgment_config.get("verdict_pass", "✅ APPROVED"),
        verdict_warning=judgment_config.get("verdict_warning", "⚠️ APPROVED WITH COMMENTS"),
        verdict_needs_work=judgment_config.get("verdict_needs_work", "🔧 NEEDS WORK"),
        verdict_reject=judgment_config.get("verdict_reject", "❌ REJECTED"),
    )

    return ReviewerMindset(
        name=name,
        role=mindsets_config.get("role", f"{name} reviewer"),
        traits=mindsets_config.get("traits", []),
        approach=mindsets_config.get("approach", {}),
        questions=mindsets_config.get("questions", {}).get("items", []),
        judgment=judgment,
    )


@dataclass
class AnalysisVerdict:
    """Result of evaluating analysis with a mindset."""

    verdict: str  # PASS, WARNING, NEEDS_WORK, REJECT
    verdict_text: str  # Full verdict message
    critical_count: int = 0
    warning_count: int = 0
    total_items: int = 0
    critical_ratio: float = 0.0
    warning_ratio: float = 0.0
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def evaluate_results(
    mindset: ReviewerMindset,
    critical_issues: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    total_items: int,
    thresholds: dict[str, Any] | None = None,
) -> AnalysisVerdict:
    """Evaluate analysis results using mindset judgment criteria.

    Args:
        mindset: Reviewer mindset to use
        critical_issues: List of critical issues found
        warnings: List of warning-level issues
        total_items: Total number of items analyzed (files, functions, etc.)
        thresholds: Optional override thresholds from config

    Returns:
        AnalysisVerdict with verdict, counts, and recommendations
    """
    critical_count = len(critical_issues)
    warning_count = len(warnings)

    # Calculate ratios (avoid division by zero)
    critical_ratio = (critical_count / total_items * 100) if total_items > 0 else 0
    warning_ratio = (warning_count / total_items * 100) if total_items > 0 else 0

    # Get thresholds from mindset or overrides
    crit_threshold = mindset.judgment.critical_threshold
    warn_threshold = mindset.judgment.warning_threshold

    if thresholds:
        crit_threshold = thresholds.get("critical_threshold", crit_threshold)
        warn_threshold = thresholds.get("warning_threshold", warn_threshold)

    # Determine verdict
    if critical_ratio > crit_threshold or critical_count > 0 and crit_threshold <= 1:
        verdict = "REJECT"
        verdict_text = mindset.judgment.verdict_reject
    elif warning_ratio > warn_threshold:
        verdict = "NEEDS_WORK"
        verdict_text = mindset.judgment.verdict_needs_work
    elif warning_count > 0:
        verdict = "WARNING"
        verdict_text = mindset.judgment.verdict_warning
    else:
        verdict = "PASS"
        verdict_text = mindset.judgment.verdict_pass

    # Generate findings summary
    findings = []
    if critical_count > 0:
        findings.append(f"🔴 {critical_count} critical issues ({critical_ratio:.1f}%)")
    if warning_count > 0:
        findings.append(f"🟠 {warning_count} warnings ({warning_ratio:.1f}%)")
    if not findings:
        findings.append("🟢 No significant issues found")

    # Generate recommendations based on mindset
    recommendations = []
    if verdict in ("REJECT", "NEEDS_WORK"):
        recommendations.append("Address critical issues before merging")
        if mindset.questions:
            recommendations.append(f"Ask yourself: {mindset.questions[0]}")

    return AnalysisVerdict(
        verdict=verdict,
        verdict_text=verdict_text,
        critical_count=critical_count,
        warning_count=warning_count,
        total_items=total_items,
        critical_ratio=critical_ratio,
        warning_ratio=warning_ratio,
        findings=findings,
        recommendations=recommendations,
    )


def format_verdict_report(
    mindset: ReviewerMindset,
    verdict: AnalysisVerdict,
    include_mindset: bool = True,
) -> str:
    """Format a complete verdict report with mindset context.

    Args:
        mindset: Reviewer mindset used
        verdict: Analysis verdict
        include_mindset: Whether to include mindset header

    Returns:
        Markdown-formatted report
    """
    lines = []

    # Mindset header (optional)
    if include_mindset:
        lines.extend(
            [
                "## Reviewer Mindset",
                "",
                mindset.format_header(),
                "",
            ]
        )

    # Verdict
    lines.extend(
        [
            "## Verdict",
            "",
            verdict.verdict_text,
            "",
        ]
    )

    # Findings
    lines.extend(
        [
            "## Findings",
            "",
        ]
    )
    for finding in verdict.findings:
        lines.append(f"- {finding}")
    lines.append("")

    # Statistics
    lines.extend(
        [
            "## Statistics",
            "",
            f"- **Total items analyzed:** {verdict.total_items}",
            f"- **Critical issues:** {verdict.critical_count} ({verdict.critical_ratio:.1f}%)",
            f"- **Warnings:** {verdict.warning_count} ({verdict.warning_ratio:.1f}%)",
            "",
        ]
    )

    # Recommendations
    if verdict.recommendations:
        lines.extend(
            [
                "## Recommendations",
                "",
            ]
        )
        for rec in verdict.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)


# Pre-defined mindset names for convenience
QUALITY_MINDSET = "quality"
SECURITY_MINDSET = "security"
DOCS_MINDSET = "docs"
PERF_MINDSET = "perf"
DEPS_MINDSET = "deps"
