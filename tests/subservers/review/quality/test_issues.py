"""Tests for quality issues module."""

import pytest

from btx_fix_mcp.subservers.review.quality.config import QualityConfig
from btx_fix_mcp.subservers.review.quality.issues import (
    Issue,
    RuleIssue,
    ThresholdIssue,
    _add_architecture_issues,
    _add_cognitive_issues,
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


class TestAddMaintainabilityIssues:
    """Tests for _add_maintainability_issues."""

    def test_add_low_maintainability_warning(self):
        """Test adding low maintainability warning."""
        issues = []
        results = {"maintainability": [{"file": "test.py", "mi": 15}]}
        _add_maintainability_issues(issues, results, threshold=20)
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_add_low_maintainability_error(self):
        """Test adding low maintainability error for very low MI."""
        issues = []
        results = {"maintainability": [{"file": "test.py", "mi": 5}]}
        _add_maintainability_issues(issues, results, threshold=20)
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"

    def test_no_issue_above_threshold(self):
        """Test no issue when above threshold."""
        issues = []
        results = {"maintainability": [{"file": "test.py", "mi": 25}]}
        _add_maintainability_issues(issues, results, threshold=20)
        assert len(issues) == 0


class TestAddFunctionIssues:
    """Tests for _add_function_issues."""

    def test_add_function_issue_warning(self):
        """Test adding function issue as warning."""
        issues = []
        results = {
            "function_issues": [
                {
                    "issue_type": "LONG_FUNCTION",
                    "file": "test.py",
                    "line": 10,
                    "function": "test_func",
                    "value": 60,
                    "threshold": 50,
                    "message": "Function too long",
                }
            ]
        }
        _add_function_issues(issues, results)
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_add_function_issue_error(self):
        """Test adding function issue as error when severely over threshold."""
        issues = []
        results = {
            "function_issues": [
                {
                    "issue_type": "LONG_FUNCTION",
                    "file": "test.py",
                    "line": 10,
                    "function": "test_func",
                    "value": 150,  # > 50*2
                    "threshold": 50,
                    "message": "Function too long",
                }
            ]
        }
        _add_function_issues(issues, results)
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"


class TestAddCognitiveIssues:
    """Tests for _add_cognitive_issues."""

    def test_add_cognitive_issue(self):
        """Test adding cognitive complexity issue."""
        issues = []
        results = {
            "cognitive": [
                {
                    "file": "test.py",
                    "line": 10,
                    "function": "complex_func",
                    "cognitive_complexity": 20,
                    "exceeds_threshold": True,
                }
            ]
        }
        _add_cognitive_issues(issues, results, threshold=15)
        assert len(issues) == 1
        assert "cognitive" in issues[0]["type"]

    def test_no_issue_if_not_exceeds(self):
        """Test no issue if exceeds_threshold is False."""
        issues = []
        results = {
            "cognitive": [
                {
                    "file": "test.py",
                    "cognitive_complexity": 10,
                    "exceeds_threshold": False,
                }
            ]
        }
        _add_cognitive_issues(issues, results, threshold=15)
        assert len(issues) == 0


class TestAddTestIssues:
    """Tests for _add_test_issues."""

    def test_add_test_issue(self):
        """Test adding test issue."""
        issues = []
        results = {
            "tests": {
                "issues": [
                    {
                        "type": "NO_ASSERTIONS",
                        "file": "test_example.py",
                        "line": 10,
                        "message": "Test has no assertions",
                    }
                ]
            }
        }
        _add_test_issues(issues, results)
        assert len(issues) == 1
        assert issues[0]["type"] == "no_assertions"


class TestAddArchitectureIssues:
    """Tests for _add_architecture_issues."""

    def test_add_god_object(self):
        """Test adding god object issue."""
        issues = []
        results = {
            "architecture": {
                "god_objects": [
                    {
                        "file": "test.py",
                        "line": 1,
                        "class": "GodClass",
                        "methods": 50,
                        "lines": 1000,
                    }
                ]
            }
        }
        _add_architecture_issues(issues, results, coupling_threshold=10)
        assert len(issues) == 1
        assert issues[0]["type"] == "god_object"

    def test_add_high_coupling(self):
        """Test adding high coupling issue."""
        issues = []
        results = {
            "architecture": {
                "highly_coupled": [
                    {
                        "file": "test.py",
                        "import_count": 20,
                        "threshold": 15,
                    }
                ]
            }
        }
        _add_architecture_issues(issues, results, coupling_threshold=15)
        assert len(issues) == 1
        assert issues[0]["type"] == "high_coupling"


class TestAddRuntimeCheckIssues:
    """Tests for _add_runtime_check_issues."""

    def test_add_runtime_check(self):
        """Test adding runtime check issue."""
        issues = []
        results = {
            "runtime_checks": [
                {
                    "file": "test.py",
                    "line": 10,
                    "function": "check_func",
                    "check_count": 5,
                    "message": "Multiple runtime checks in function",
                }
            ]
        }
        _add_runtime_check_issues(issues, results)
        assert len(issues) == 1
        assert issues[0]["severity"] == "info"


class TestAddRuffIssues:
    """Tests for _add_ruff_issues."""

    def test_add_ruff_issue(self, tmp_path):
        """Test adding Ruff issue."""
        issues = []
        results = {
            "static": {
                "ruff_json": [
                    {
                        "filename": str(tmp_path / "test.py"),
                        "code": "E501",
                        "message": "Line too long",
                        "location": {"row": 10},
                    }
                ]
            }
        }
        _add_ruff_issues(issues, results, tmp_path)
        assert len(issues) == 1
        assert "ruff" in issues[0]["type"]

    def test_add_ruff_issue_relative_path_error(self, tmp_path):
        """Test handling of non-relative path."""
        issues = []
        results = {
            "static": {
                "ruff_json": [
                    {
                        "filename": "/other/path/test.py",
                        "code": "E501",
                        "message": "Line too long",
                        "location": {"row": 10},
                    }
                ]
            }
        }
        _add_ruff_issues(issues, results, tmp_path)
        assert len(issues) == 1
        assert issues[0]["file"] == "/other/path/test.py"


class TestAddDuplicationIssues:
    """Tests for _add_duplication_issues."""

    def test_add_duplication_issue(self):
        """Test adding duplication issue."""
        issues = []
        results = {"duplication": {"duplicates": ["Similar lines in file1.py and file2.py"]}}
        _add_duplication_issues(issues, results)
        assert len(issues) == 1
        assert issues[0]["type"] == "code_duplication"


class TestAddCoverageIssues:
    """Tests for _add_coverage_issues."""

    def test_add_low_type_coverage(self):
        """Test adding low type coverage issue."""
        issues = []
        results = {"type_coverage": {"coverage_percent": 50}}
        _add_coverage_issues(issues, results, min_type_coverage=80, min_docstring_coverage=80)
        assert len(issues) == 1
        assert issues[0]["type"] == "low_type_coverage"

    def test_add_low_docstring_coverage(self):
        """Test adding low docstring coverage issue."""
        issues = []
        results = {"docstring_coverage": {"coverage_percent": 60}}
        _add_coverage_issues(issues, results, min_type_coverage=50, min_docstring_coverage=80)
        assert len(issues) == 1
        assert issues[0]["type"] == "low_docstring_coverage"

    def test_no_coverage_issues_above_threshold(self):
        """Test no issues when coverage is above threshold."""
        issues = []
        results = {
            "type_coverage": {"coverage_percent": 90},
            "docstring_coverage": {"coverage_percent": 85},
        }
        _add_coverage_issues(issues, results, min_type_coverage=80, min_docstring_coverage=80)
        assert len(issues) == 0


class TestCompileAllIssues:
    """Tests for compile_all_issues function."""

    @pytest.fixture
    def config(self):
        """Create a default QualityConfig."""
        return QualityConfig()

    def test_compile_empty_results(self, tmp_path, config):
        """Test compiling issues from empty results."""
        issues = compile_all_issues({}, config, tmp_path)
        assert issues == []

    def test_compile_issues_mixed(self, tmp_path, config):
        """Test compiling multiple types of issues."""
        results = {
            "maintainability": [{"file": "test.py", "mi": 5}],
            "tests": {
                "issues": [
                    {
                        "type": "NO_ASSERTIONS",
                        "file": "test_example.py",
                        "message": "Test has no assertions",
                    }
                ]
            },
        }
        issues = compile_all_issues(results, config, tmp_path)
        assert len(issues) >= 2
