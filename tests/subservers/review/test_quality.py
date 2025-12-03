"""Tests for Quality sub-server."""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from glintefy.subservers.review.quality import QualitySubServer


class TestQualitySubServer:
    """Tests for QualitySubServer class."""

    @pytest.fixture
    def scope_output(self, tmp_path):
        """Create mock scope output directory with files list."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()

        # Create files_to_review.txt
        files_list = scope_dir / "files_to_review.txt"
        files_list.write_text("main.py\nutils.py\ntest_main.py\n")

        # Create files_code.txt (Python files)
        code_files = scope_dir / "files_code.txt"
        code_files.write_text("main.py\nutils.py\n")

        return scope_dir

    @pytest.fixture
    def repo_with_code(self, tmp_path):
        """Create repo with Python files for analysis."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Simple function (low complexity)
        (repo_dir / "simple.py").write_text('''
def add(a, b):
    """Add two numbers."""
    return a + b
''')

        # Complex function (high complexity)
        (repo_dir / "complex.py").write_text('''
def process(data, flag1, flag2, flag3):
    """Complex function with many branches."""
    result = []
    if flag1:
        if data:
            for item in data:
                if item > 0:
                    if flag2:
                        result.append(item * 2)
                    elif flag3:
                        result.append(item * 3)
                    else:
                        result.append(item)
                else:
                    if flag2 and flag3:
                        result.append(0)
                    else:
                        result.append(-1)
        else:
            result = [0]
    else:
        result = []
    return result
''')

        return repo_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        output_dir = tmp_path / "output"
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        assert server.name == "quality"
        assert server.quality_config.thresholds.complexity == 10
        assert server.quality_config.thresholds.maintainability == 20

    def test_initialization_custom_thresholds(self, tmp_path):
        """Test initialization with custom thresholds."""
        output_dir = tmp_path / "output"
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            complexity_threshold=15,
            maintainability_threshold=25,
        )

        assert server.quality_config.thresholds.complexity == 15
        assert server.quality_config.thresholds.maintainability == 25

    def test_validate_inputs_missing_files_list(self, tmp_path):
        """Test validation fails without files list."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No files list" in m for m in missing)

    def test_validate_inputs_success(self, scope_output, tmp_path):
        """Test validation succeeds with files list."""
        output_dir = tmp_path / "output"

        server = QualitySubServer(
            input_dir=scope_output,
            output_dir=output_dir,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_execute_no_python_files(self, tmp_path):
        """Test execution with no Python files."""
        # Create scope output with no Python files
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_to_review.txt").write_text("README.md\nconfig.yaml\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["files_analyzed"] == 0

    def test_execute_with_simple_code(self, tmp_path):
        """Test execution with simple Python code."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "simple.py").write_text('''
def hello():
    """Return greeting."""
    return "world"
''')

        # Create tests directory with a simple test for beartype
        tests_dir = repo_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_simple.py").write_text('''
"""Tests for simple module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from simple import hello

def test_hello():
    """Test hello returns world."""
    assert hello() == "world"
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("simple.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["files_analyzed"] == 1
        # May have warnings for type/docstring coverage, but no critical issues
        assert result.metrics.get("critical_issues", 0) == 0

    def test_execute_with_complex_code(self, repo_with_code, tmp_path):
        """Test execution with complex Python code."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("complex.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_code,
            complexity_threshold=5,  # Lower threshold to catch issues
        )

        result = server.run()

        # Should find complexity issues
        assert result.status in ("SUCCESS", "PARTIAL")
        assert result.metrics["files_analyzed"] == 1

    def test_artifacts_created(self, repo_with_code, tmp_path):
        """Test that artifact files are created."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("simple.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_code,
        )

        result = server.run()

        # Check artifacts exist
        assert "complexity" in result.artifacts
        assert result.artifacts["complexity"].exists()
        assert "maintainability" in result.artifacts
        assert result.artifacts["maintainability"].exists()

    def test_summary_format(self, repo_with_code, tmp_path):
        """Test summary is properly formatted."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("simple.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_code,
        )

        result = server.run()

        assert result.summary.startswith("# Quality Analysis Report")
        assert "## Overview" in result.summary
        assert "Files Analyzed" in result.summary

    def test_integration_protocol_compliance(self, repo_with_code, tmp_path):
        """Test integration protocol compliance."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("simple.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_with_code,
        )

        server.run()

        # Check protocol files
        assert (output_dir / "status.txt").exists()
        assert (output_dir / "quality_summary.md").exists()

    def test_config_from_parameters(self, tmp_path):
        """Test configuration via constructor parameters."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_to_review.txt").write_text("")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
            complexity_threshold=15,
            maintainability_threshold=30,
        )

        assert server.quality_config.thresholds.complexity == 15
        assert server.quality_config.thresholds.maintainability == 30


class TestQualitySubServerIntegration:
    """Integration tests with actual radon analysis."""

    def test_full_analysis_workflow(self, tmp_path):
        """Test complete analysis workflow."""
        # Create repo with code
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "app.py").write_text('''
"""Main application module."""

def calculate_total(items, tax_rate=0.1):
    """Calculate total with tax."""
    subtotal = sum(items)
    tax = subtotal * tax_rate
    return subtotal + tax

def format_currency(amount):
    """Format amount as currency."""
    return f"${amount:.2f}"
''')

        # Create tests directory with tests for beartype
        tests_dir = repo_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_app.py").write_text('''
"""Tests for app module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import calculate_total, format_currency

def test_calculate_total():
    """Test total calculation."""
    assert calculate_total([10, 20, 30]) == 66.0

def test_format_currency():
    """Test currency formatting."""
    assert format_currency(99.9) == "$99.90"
''')

        # Create scope output
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("app.py\n")

        # Run quality analysis
        output_dir = tmp_path / "quality"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["files_analyzed"] == 1
        assert result.metrics["total_functions"] >= 2  # At least 2 functions
        assert "complexity" in result.artifacts


class TestQualitySubServerParallel:
    """Tests for parallel analyzer execution."""

    def test_analyzers_run_in_parallel(self, tmp_path):
        """Test that analyzers are executed in parallel."""
        # Create repo with code
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "code.py").write_text('''
def foo():
    """Test function."""
    return 42
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("code.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        # Track which analyzers were called
        called_analyzers = []

        # Mock all analyzers to track calls (access via orchestrator)
        original_complexity = server.orchestrator.complexity_analyzer.analyze
        original_static = server.orchestrator.static_analyzer.analyze
        original_test = server.orchestrator.test_analyzer.analyze
        original_arch = server.orchestrator.architecture_analyzer.analyze
        original_metrics = server.orchestrator.metrics_analyzer.analyze
        original_types = server.orchestrator.type_analyzer.analyze

        def make_mock(name, original):
            def mock_analyze(files):
                called_analyzers.append((name, time.time()))
                return original(files)

            return mock_analyze

        server.orchestrator.complexity_analyzer.analyze = make_mock("complexity", original_complexity)
        server.orchestrator.static_analyzer.analyze = make_mock("static", original_static)
        server.orchestrator.test_analyzer.analyze = make_mock("tests", original_test)
        server.orchestrator.architecture_analyzer.analyze = make_mock("architecture", original_arch)
        server.orchestrator.metrics_analyzer.analyze = make_mock("metrics", original_metrics)
        server.orchestrator.type_analyzer.analyze = make_mock("types", original_types)

        result = server.run()

        assert result.status in ("SUCCESS", "PARTIAL")
        # Verify multiple analyzers were called
        assert len(called_analyzers) >= 4  # At least complexity, static, architecture, metrics

    def test_parallel_execution_uses_thread_pool(self, tmp_path):
        """Test that _run_analyzers_parallel uses ThreadPoolExecutor."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "test.py").write_text("x = 1")

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("test.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        python_files = [str(repo_dir / "test.py")]
        js_files = []

        # Patch ThreadPoolExecutor to verify it's used
        with patch("glintefy.subservers.review.quality.orchestrator.ThreadPoolExecutor", wraps=ThreadPoolExecutor) as mock_executor:
            server.orchestrator.run_all(python_files, js_files)
            # Verify ThreadPoolExecutor was called
            assert mock_executor.called

    def test_parallel_handles_analyzer_failure(self, tmp_path):
        """Test that parallel execution handles individual analyzer failures gracefully."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "code.py").write_text("x = 1")

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("code.py\n")

        output_dir = tmp_path / "output"
        server = QualitySubServer(
            input_dir=scope_dir,
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        # Make one analyzer fail
        def failing_analyze(files):
            raise RuntimeError("Simulated failure")

        server.orchestrator.test_analyzer.analyze = failing_analyze

        # Should still complete without raising
        result = server.orchestrator.run_all([str(repo_dir / "code.py")], [])

        # Should complete with results from other analyzers (complexity at minimum)
        assert isinstance(result.complexity, list) or isinstance(result.maintainability, list)
