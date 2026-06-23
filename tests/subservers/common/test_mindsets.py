"""Tests for reviewer mindsets module."""

import pytest

from glintefy.subservers.common.mindsets import (
    QUALITY_MINDSET,
    SECURITY_MINDSET,
    AnalysisVerdict,
    JudgmentCriteria,
    ReviewerMindset,
    evaluate_results,
    format_verdict_report,
    get_mindset,
)


class TestJudgmentCriteria:
    """Tests for JudgmentCriteria dataclass."""

    def test_default_values(self):
        """Test default judgment criteria values."""
        criteria = JudgmentCriteria()

        assert criteria.critical_threshold == 10.0
        assert criteria.warning_threshold == 25.0
        assert criteria.verdict_pass == "[PASS] APPROVED"
        assert criteria.verdict_reject == "[FAIL] REJECTED"

    def test_custom_values(self):
        """Test custom judgment criteria values."""
        criteria = JudgmentCriteria(
            critical_threshold=5.0,
            warning_threshold=15.0,
            verdict_pass="PASS",
            verdict_reject="FAIL",
        )

        assert criteria.critical_threshold == 5.0
        assert criteria.warning_threshold == 15.0


class TestReviewerMindset:
    """Tests for ReviewerMindset dataclass."""

    @pytest.fixture
    def sample_mindset(self):
        """Create a sample mindset for testing."""
        return ReviewerMindset(
            name="test",
            role="test reviewer",
            traits=["thorough", "precise"],
            approach={"verify": "Verify all claims", "measure": "Measure everything"},
            questions=["Is this correct?", "Let me verify."],
            judgment=JudgmentCriteria(),
        )

    def test_format_header(self, sample_mindset):
        """Test formatting mindset as header."""
        header = sample_mindset.format_header()

        assert "test reviewer" in header
        assert "thorough" in header
        assert "precise" in header

    def test_format_approach(self, sample_mindset):
        """Test formatting approach as bullet points."""
        approach = sample_mindset.format_approach()

        assert "Your approach" in approach
        assert "Verify all claims" in approach
        assert "Measure everything" in approach

    def test_format_questions(self, sample_mindset):
        """Test formatting questions as bullet points."""
        questions = sample_mindset.format_questions()

        assert "Your Questions" in questions
        assert "Is this correct?" in questions
        assert "Let me verify." in questions

    def test_format_full(self, sample_mindset):
        """Test full mindset formatting."""
        full = sample_mindset.format_full()

        assert "test reviewer" in full
        assert "Your approach" in full
        assert "Your Questions" in full

    def test_format_for_tool_description(self, sample_mindset):
        """Test formatting for MCP tool description."""
        desc = sample_mindset.format_for_tool_description()

        assert "test reviewer" in desc
        assert "APPROACH:" in desc
        assert "QUESTIONS TO ASK:" in desc


class TestGetMindset:
    """Tests for get_mindset function."""

    def test_get_quality_mindset(self):
        """Test loading quality mindset."""
        mindset = get_mindset(QUALITY_MINDSET)

        assert mindset.name == "quality"
        assert "quality" in mindset.role.lower() or "meticulous" in mindset.role.lower()

    def test_get_security_mindset(self):
        """Test loading security mindset."""
        mindset = get_mindset(SECURITY_MINDSET)

        assert mindset.name == "security"

    def test_get_unknown_mindset_returns_default(self):
        """Test that unknown mindset returns default."""
        mindset = get_mindset("unknown_mindset")

        assert mindset.name == "unknown_mindset"
        assert "reviewer" in mindset.role
        assert len(mindset.traits) > 0

    def test_get_mindset_with_custom_config(self):
        """Test loading mindset with custom config."""
        custom_config = {
            "review": {
                "mindsets": {
                    "custom": {
                        "role": "custom reviewer",
                        "traits": ["custom1", "custom2"],
                        "approach": {"key": "value"},
                        "questions": {"items": ["Q1?", "Q2?"]},
                        "judgment": {
                            "critical_threshold": 5.0,
                            "verdict_pass": "CUSTOM PASS",
                        },
                    }
                }
            }
        }

        mindset = get_mindset("custom", custom_config)

        assert mindset.role == "custom reviewer"
        assert mindset.traits == ["custom1", "custom2"]
        assert mindset.judgment.critical_threshold == 5.0
        assert mindset.judgment.verdict_pass == "CUSTOM PASS"


class TestEvaluateResults:
    """Tests for evaluate_results function."""

    @pytest.fixture
    def mindset(self):
        """Create a mindset for testing."""
        return ReviewerMindset(
            name="test",
            role="test reviewer",
            traits=["thorough"],
            approach={"verify": "Verify"},
            questions=["Is this correct?"],
            judgment=JudgmentCriteria(
                critical_threshold=10.0,
                warning_threshold=25.0,
            ),
        )

    def test_pass_verdict_no_issues(self, mindset):
        """Test PASS verdict when no issues."""
        verdict = evaluate_results(mindset, [], [], 100)

        assert verdict.verdict == "PASS"
        assert "APPROVED" in verdict.verdict_text
        assert verdict.critical_count == 0
        assert verdict.warning_count == 0

    def test_warning_verdict_few_warnings(self, mindset):
        """Test WARNING verdict with some warnings."""
        warnings = [{"issue": "w1"}, {"issue": "w2"}]
        verdict = evaluate_results(mindset, [], warnings, 100)

        assert verdict.verdict == "WARNING"
        assert verdict.warning_count == 2

    def test_needs_work_verdict_many_warnings(self, mindset):
        """Test NEEDS_WORK verdict with many warnings."""
        # 30 warnings out of 100 items = 30%, exceeds 25% threshold
        warnings = [{"issue": f"w{i}"} for i in range(30)]
        verdict = evaluate_results(mindset, [], warnings, 100)

        assert verdict.verdict == "NEEDS_WORK"

    def test_reject_verdict_critical_issues(self, mindset):
        """Test REJECT verdict with critical issues."""
        # 15 critical out of 100 = 15%, exceeds 10% threshold
        critical = [{"issue": f"c{i}"} for i in range(15)]
        verdict = evaluate_results(mindset, critical, [], 100)

        assert verdict.verdict == "REJECT"
        assert "REJECTED" in verdict.verdict_text

    def test_findings_summary(self, mindset):
        """Test findings are summarized correctly."""
        critical = [{"issue": "c1"}]
        warnings = [{"issue": "w1"}, {"issue": "w2"}]
        verdict = evaluate_results(mindset, critical, warnings, 100)

        assert any("critical" in f.lower() for f in verdict.findings)
        assert any("warning" in f.lower() for f in verdict.findings)

    def test_recommendations_for_reject(self, mindset):
        """Test recommendations are generated for rejected code."""
        critical = [{"issue": f"c{i}"} for i in range(15)]
        verdict = evaluate_results(mindset, critical, [], 100)

        assert len(verdict.recommendations) > 0
        assert any("critical" in r.lower() for r in verdict.recommendations)

    def test_custom_thresholds(self, mindset):
        """Test custom threshold overrides."""
        # Only 5 critical out of 100 = 5%, normally would pass
        # But with threshold override of 3%, should reject
        critical = [{"issue": f"c{i}"} for i in range(5)]
        verdict = evaluate_results(mindset, critical, [], 100, thresholds={"critical_threshold": 3.0})

        assert verdict.verdict == "REJECT"


class TestFormatVerdictReport:
    """Tests for format_verdict_report function."""

    @pytest.fixture
    def mindset(self):
        """Create a mindset for testing."""
        return ReviewerMindset(
            name="test",
            role="test reviewer",
            traits=["thorough"],
            approach={"verify": "Verify"},
            questions=["Is this correct?"],
        )

    @pytest.fixture
    def verdict(self):
        """Create a verdict for testing."""
        return AnalysisVerdict(
            verdict="WARNING",
            verdict_text="[WARN] APPROVED WITH COMMENTS",
            critical_count=0,
            warning_count=5,
            total_items=100,
            critical_ratio=0.0,
            warning_ratio=5.0,
            findings=["🟠 5 warnings (5.0%)"],
            recommendations=["Address warnings"],
        )

    def test_report_includes_verdict(self, mindset, verdict):
        """Test report includes verdict section."""
        report = format_verdict_report(mindset, verdict)

        assert "## Verdict" in report
        assert verdict.verdict_text in report

    def test_report_includes_findings(self, mindset, verdict):
        """Test report includes findings section."""
        report = format_verdict_report(mindset, verdict)

        assert "## Findings" in report
        assert "5 warnings" in report

    def test_report_includes_statistics(self, mindset, verdict):
        """Test report includes statistics section."""
        report = format_verdict_report(mindset, verdict)

        assert "## Statistics" in report
        assert "100" in report  # total items

    def test_report_includes_mindset_when_requested(self, mindset, verdict):
        """Test report includes mindset header when requested."""
        report = format_verdict_report(mindset, verdict, include_mindset=True)

        assert "## Reviewer Mindset" in report
        assert "test reviewer" in report

    def test_report_excludes_mindset_when_not_requested(self, mindset, verdict):
        """Test report excludes mindset header when not requested."""
        report = format_verdict_report(mindset, verdict, include_mindset=False)

        assert "## Reviewer Mindset" not in report

    def test_report_includes_recommendations(self, mindset, verdict):
        """Test report includes recommendations."""
        report = format_verdict_report(mindset, verdict)

        assert "## Recommendations" in report
        assert "Address warnings" in report
