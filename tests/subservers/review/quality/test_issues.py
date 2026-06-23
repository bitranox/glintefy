"""Tests for quality issues module."""

import pytest

from glintefy.subservers.common.issues import DocstringCoverageMetrics, TypeCoverageMetrics
from glintefy.subservers.review.quality.analyzer_results import (
    ArchitectureMetrics,
    CognitiveComplexityItem,
    CyclomaticComplexityItem,
    DuplicationResults,
    FunctionIssueItem,
    GodObjectInfo,
    HighCouplingInfo,
    MaintainabilityItem,
    QualityAnalysisResults,
    RuffDiagnostic,
    RuffLocation,
    RuffResults,
    RuntimeCheckInfo,
    SuiteIssueItem,
    SuiteResults,
)
from glintefy.subservers.review.quality.config import QualityConfig
from glintefy.subservers.review.quality.issues import (
    Issue,
    RuleIssue,
    ThresholdIssue,
    _add_architecture_issues,
    _add_cognitive_issues,
    _add_complexity_issues,
    _add_coverage_issues,
    _add_duplication_issues,
    _add_function_issues,
    _add_maintainability_issues,
    _add_ruff_issues,
    _add_runtime_check_issues,
    _add_test_issues,
    compile_all_issues,
)


class TestIssueDataclasses:
    """Tests for issue dataclasses."""

    def test_issue_to_dict(self):
        """Test Issue.to_dict()."""
        issue = Issue(
            type="test_issue",
            severity="warning",
            file="test.py",
            line=10,
            message="Test message",
        )
        d = issue.to_dict()
        assert d["type"] == "test_issue"
        assert d["severity"] == "warning"
        assert d["file"] == "test.py"
        assert d["line"] == 10
        assert d["message"] == "Test message"

    def test_threshold_issue_to_dict(self):
        """Test ThresholdIssue.to_dict()."""
        issue = ThresholdIssue(
            type="threshold_issue",
            severity="error",
            file="test.py",
            value=15,
            threshold=10,
            message="Value exceeds threshold",
        )
        d = issue.to_dict()
        assert d["value"] == 15
        assert d["threshold"] == 10

    def test_rule_issue_to_dict(self):
        """Test RuleIssue.to_dict()."""
        issue = RuleIssue(
            type="rule_issue",
            severity="info",
            file="test.py",
            rule="E501",
            message="Line too long",
        )
        d = issue.to_dict()
        assert d["rule"] == "E501"


class TestAddComplexityIssues:
    """Tests for _add_complexity_issues."""

    def test_add_high_complexity_warning(self):
        """Test adding high complexity warning."""
        issues = []
        results = QualityAnalysisResults(complexity=[CyclomaticComplexityItem(file="test.py", name="func", type="function", complexity=15, rank="C", line=10)])
        _add_complexity_issues(issues, results, threshold=10, error_threshold=20)
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_add_high_complexity_error(self):
        """Test adding high complexity error for very high complexity."""
        issues = []
        results = QualityAnalysisResults(complexity=[CyclomaticComplexityItem(file="test.py", name="func", type="function", complexity=25, rank="E", line=10)])
        _add_complexity_issues(issues, results, threshold=10, error_threshold=20)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_no_issue_below_threshold(self):
        """Test no issue when below threshold."""
        issues = []
        results = QualityAnalysisResults(complexity=[CyclomaticComplexityItem(file="test.py", name="func", type="function", complexity=5, rank="A", line=10)])
        _add_complexity_issues(issues, results, threshold=10, error_threshold=20)
        assert len(issues) == 0

    def test_error_threshold_configurable(self):
        """Test that error threshold is configurable."""
        issues = []
        # Complexity of 12 with error_threshold of 10 should be error
        results = QualityAnalysisResults(complexity=[CyclomaticComplexityItem(file="test.py", name="func", type="function", complexity=12, rank="C", line=10)])
        _add_complexity_issues(issues, results, threshold=5, error_threshold=10)
        assert len(issues) == 1
        assert issues[0].severity == "error"


class TestAddMaintainabilityIssues:
    """Tests for _add_maintainability_issues."""

    def test_add_low_maintainability_warning(self):
        """Test adding low maintainability warning."""
        issues = []
        results = QualityAnalysisResults(maintainability=[MaintainabilityItem(file="test.py", mi=15.0, rank="B")])
        _add_maintainability_issues(issues, results, threshold=20, error_threshold=10)
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_add_low_maintainability_error(self):
        """Test adding low maintainability error for very low MI."""
        issues = []
        results = QualityAnalysisResults(maintainability=[MaintainabilityItem(file="test.py", mi=5.0, rank="C")])
        _add_maintainability_issues(issues, results, threshold=20, error_threshold=10)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_no_issue_above_threshold(self):
        """Test no issue when above threshold."""
        issues = []
        results = QualityAnalysisResults(maintainability=[MaintainabilityItem(file="test.py", mi=25.0, rank="A")])
        _add_maintainability_issues(issues, results, threshold=20, error_threshold=10)
        assert len(issues) == 0

    def test_error_threshold_configurable(self):
        """Test that error threshold is configurable."""
        issues = []
        # MI of 15 with error_threshold of 20 should be error
        results = QualityAnalysisResults(maintainability=[MaintainabilityItem(file="test.py", mi=15.0, rank="B")])
        _add_maintainability_issues(issues, results, threshold=25, error_threshold=20)
        assert len(issues) == 1
        assert issues[0].severity == "error"


class TestAddFunctionIssues:
    """Tests for _add_function_issues."""

    def test_add_function_issue_warning(self):
        """Test adding function issue as warning."""
        issues = []
        results = QualityAnalysisResults(
            function_issues=[
                FunctionIssueItem(
                    file="test.py",
                    function="test_func",
                    line=10,
                    issue_type="LONG_FUNCTION",
                    value=60,
                    threshold=50,
                    message="Function too long",
                )
            ]
        )
        _add_function_issues(issues, results)
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_add_function_issue_error(self):
        """Test adding function issue as error when severely over threshold."""
        issues = []
        results = QualityAnalysisResults(
            function_issues=[
                FunctionIssueItem(
                    file="test.py",
                    function="test_func",
                    line=10,
                    issue_type="LONG_FUNCTION",
                    value=150,  # > 50*2
                    threshold=50,
                    message="Function too long",
                )
            ]
        )
        _add_function_issues(issues, results)
        assert len(issues) == 1
        assert issues[0].severity == "error"


class TestAddCognitiveIssues:
    """Tests for _add_cognitive_issues."""

    def test_add_cognitive_issue(self):
        """Test adding cognitive complexity issue."""
        issues = []
        results = QualityAnalysisResults(
            cognitive=[
                CognitiveComplexityItem(
                    file="test.py",
                    name="complex_func",
                    line=10,
                    complexity=20,
                    exceeds_threshold=True,
                )
            ]
        )
        _add_cognitive_issues(issues, results, threshold=15)
        assert len(issues) == 1
        assert "cognitive" in issues[0].type

    def test_no_issue_if_not_exceeds(self):
        """Test no issue if exceeds_threshold is False."""
        issues = []
        results = QualityAnalysisResults(
            cognitive=[
                CognitiveComplexityItem(
                    file="test.py",
                    name="simple_func",
                    line=5,
                    complexity=10,
                    exceeds_threshold=False,
                )
            ]
        )
        _add_cognitive_issues(issues, results, threshold=15)
        assert len(issues) == 0


class TestAddTestIssues:
    """Tests for _add_test_issues."""

    def test_add_test_issue(self):
        """Test adding test issue."""
        issues = []
        results = QualityAnalysisResults(
            tests=SuiteResults(
                issues=[
                    SuiteIssueItem(
                        type="NO_ASSERTIONS",
                        file="test_example.py",
                        line=10,
                        message="Test has no assertions",
                    )
                ]
            )
        )
        _add_test_issues(issues, results)
        assert len(issues) == 1
        assert issues[0].type == "no_assertions"


class TestAddArchitectureIssues:
    """Tests for _add_architecture_issues."""

    def test_add_god_object(self):
        """Test adding god object issue."""
        issues = []
        results = QualityAnalysisResults(
            architecture=ArchitectureMetrics(
                god_objects=[
                    GodObjectInfo(
                        file="test.py",
                        class_name="GodClass",
                        line=1,
                        methods=50,
                        lines=1000,
                        methods_threshold=20,
                        lines_threshold=500,
                    )
                ]
            )
        )
        _add_architecture_issues(issues, results, coupling_threshold=10)
        assert len(issues) == 1
        assert issues[0].type == "god_object"

    def test_add_high_coupling(self):
        """Test adding high coupling issue."""
        issues = []
        results = QualityAnalysisResults(
            architecture=ArchitectureMetrics(
                highly_coupled=[
                    HighCouplingInfo(
                        file="test.py",
                        import_count=20,
                        threshold=15,
                    )
                ]
            )
        )
        _add_architecture_issues(issues, results, coupling_threshold=15)
        assert len(issues) == 1
        assert issues[0].type == "high_coupling"


class TestAddRuntimeCheckIssues:
    """Tests for _add_runtime_check_issues."""

    def test_add_runtime_check(self):
        """Test adding runtime check issue."""
        issues = []
        results = QualityAnalysisResults(
            runtime_checks=[
                RuntimeCheckInfo(
                    file="test.py",
                    function="check_func",
                    line=10,
                    check_count=5,
                    message="Multiple runtime checks in function",
                )
            ]
        )
        _add_runtime_check_issues(issues, results)
        assert len(issues) == 1
        assert issues[0].severity == "info"


class TestAddRuffIssues:
    """Tests for _add_ruff_issues."""

    def test_add_ruff_issue(self, tmp_path):
        """Test adding Ruff issue."""
        issues = []
        results = QualityAnalysisResults(
            static=RuffResults(
                ruff_json=[
                    RuffDiagnostic(
                        filename=str(tmp_path / "test.py"),
                        code="E501",
                        message="Line too long",
                        location=RuffLocation(row=10),
                    )
                ]
            )
        )
        _add_ruff_issues(issues, results, tmp_path)
        assert len(issues) == 1
        assert "ruff" in issues[0].type

    def test_add_ruff_issue_relative_path_error(self, tmp_path):
        """Test handling of non-relative path."""
        issues = []
        results = QualityAnalysisResults(
            static=RuffResults(
                ruff_json=[
                    RuffDiagnostic(
                        filename="/other/path/test.py",
                        code="E501",
                        message="Line too long",
                        location=RuffLocation(row=10),
                    )
                ]
            )
        )
        _add_ruff_issues(issues, results, tmp_path)
        assert len(issues) == 1
        assert issues[0].file == "/other/path/test.py"


class TestAddDuplicationIssues:
    """Tests for _add_duplication_issues."""

    def test_add_duplication_issue(self):
        """Test adding duplication issue."""
        issues = []
        results = QualityAnalysisResults(duplication=DuplicationResults(duplicates=["Similar lines in file1.py and file2.py"]))
        _add_duplication_issues(issues, results)
        assert len(issues) == 1
        assert issues[0].type == "code_duplication"


class TestAddCoverageIssues:
    """Tests for _add_coverage_issues."""

    def test_add_low_type_coverage(self):
        """Test adding low type coverage issue."""
        issues = []
        results = QualityAnalysisResults(
            type_coverage=TypeCoverageMetrics(coverage_percent=50),
            docstring_coverage=DocstringCoverageMetrics(coverage_percent=100),
        )
        _add_coverage_issues(issues, results, min_type_coverage=80, min_docstring_coverage=80)
        assert len(issues) == 1
        assert issues[0].type == "low_type_coverage"

    def test_add_low_docstring_coverage(self):
        """Test adding low docstring coverage issue."""
        issues = []
        results = QualityAnalysisResults(
            type_coverage=TypeCoverageMetrics(coverage_percent=100),
            docstring_coverage=DocstringCoverageMetrics(coverage_percent=60),
        )
        _add_coverage_issues(issues, results, min_type_coverage=50, min_docstring_coverage=80)
        assert len(issues) == 1
        assert issues[0].type == "low_docstring_coverage"

    def test_no_coverage_issues_above_threshold(self):
        """Test no issues when coverage is above threshold."""
        issues = []
        results = QualityAnalysisResults(
            type_coverage=TypeCoverageMetrics(coverage_percent=90),
            docstring_coverage=DocstringCoverageMetrics(coverage_percent=85),
        )
        _add_coverage_issues(issues, results, min_type_coverage=80, min_docstring_coverage=80)
        assert len(issues) == 0


class TestCompileAllIssues:
    """Tests for compile_all_issues function."""

    @pytest.fixture
    def config(self):
        """Create a default QualityConfig."""
        return QualityConfig()

    def test_compile_empty_results(self, tmp_path, config):
        """Test compiling issues from empty results with passing coverage."""
        # Provide coverage values above thresholds to avoid coverage issues
        results = QualityAnalysisResults(
            type_coverage=TypeCoverageMetrics(coverage_percent=100),
            docstring_coverage=DocstringCoverageMetrics(coverage_percent=100),
        )
        issues = compile_all_issues(results, config, tmp_path)
        assert issues == []

    def test_compile_issues_mixed(self, tmp_path, config):
        """Test compiling multiple types of issues."""
        results = QualityAnalysisResults(
            maintainability=[MaintainabilityItem(file="test.py", mi=5.0, rank="C")],
            tests=SuiteResults(
                issues=[
                    SuiteIssueItem(
                        type="NO_ASSERTIONS",
                        file="test_example.py",
                        line=0,
                        message="Test has no assertions",
                    )
                ]
            ),
            type_coverage=TypeCoverageMetrics(coverage_percent=100),
            docstring_coverage=DocstringCoverageMetrics(coverage_percent=100),
        )
        issues = compile_all_issues(results, config, tmp_path)
        assert len(issues) >= 2
