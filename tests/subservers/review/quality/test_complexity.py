"""Tests for ComplexityAnalyzer."""

import logging

import pytest

from glintefy.subservers.review.quality.analyzer_results import ComplexityResults
from glintefy.subservers.review.quality.complexity import ComplexityAnalyzer


@pytest.fixture
def complexity_logger():
    """Create a logger for tests."""
    return logging.getLogger("test_complexity")


class TestComplexityAnalyzerBasic:
    """Basic tests for ComplexityAnalyzer."""

    @pytest.fixture
    def analyzer(self, tmp_path, complexity_logger):
        """Create a ComplexityAnalyzer instance."""
        return ComplexityAnalyzer(
            repo_path=tmp_path,
            logger=complexity_logger,
            config={},
        )

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert isinstance(result, ComplexityResults)
        assert result.complexity == []
        assert result.cognitive == []
        assert result.maintainability == []

    def test_analyze_simple_file(self, analyzer, tmp_path):
        """Test analyze with simple file."""
        code = tmp_path / "simple.py"
        code.write_text("def foo():\n    return 1\n")

        result = analyzer.analyze([str(code)])

        assert isinstance(result, ComplexityResults)
        assert isinstance(result.complexity, list)
        assert isinstance(result.maintainability, list)


class TestCyclomaticComplexity:
    """Tests for cyclomatic complexity analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, complexity_logger):
        """Create a ComplexityAnalyzer instance."""
        return ComplexityAnalyzer(
            repo_path=tmp_path,
            logger=complexity_logger,
            config={"complexity_threshold": 10},
        )

    def test_simple_function(self, analyzer, tmp_path):
        """Test complexity of simple function."""
        code = tmp_path / "simple.py"
        code.write_text("def foo():\n    return 1\n")

        result = analyzer._analyze_cyclomatic([str(code)])

        assert isinstance(result, list)

    def test_complex_function(self, analyzer, tmp_path):
        """Test complexity of complex function with conditionals."""
        code = tmp_path / "complex.py"
        code.write_text("""
def complex_func(x):
    if x > 10:
        if x > 20:
            return 'high'
        else:
            return 'medium'
    elif x > 5:
        return 'low'
    else:
        return 'very low'
""")

        result = analyzer._analyze_cyclomatic([str(code)])

        assert isinstance(result, list)


class TestCognitiveComplexity:
    """Tests for cognitive complexity analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, complexity_logger):
        """Create a ComplexityAnalyzer instance."""
        return ComplexityAnalyzer(
            repo_path=tmp_path,
            logger=complexity_logger,
            config={"cognitive_threshold": 15},
        )

    def test_simple_function_cognitive(self, analyzer, tmp_path):
        """Test cognitive complexity of simple function."""
        code = tmp_path / "simple.py"
        code.write_text("def foo():\n    return 1\n")

        result = analyzer._analyze_cognitive([str(code)])

        assert isinstance(result, list)

    def test_nested_loops_cognitive(self, analyzer, tmp_path):
        """Test cognitive complexity with nested loops."""
        code = tmp_path / "nested.py"
        code.write_text("""
def nested_func():
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(i, j, k)
""")

        result = analyzer._analyze_cognitive([str(code)])

        assert isinstance(result, list)


class TestMaintainabilityIndex:
    """Tests for maintainability index analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, complexity_logger):
        """Create a ComplexityAnalyzer instance."""
        return ComplexityAnalyzer(
            repo_path=tmp_path,
            logger=complexity_logger,
            config={"maintainability_threshold": 20},
        )

    def test_simple_file_maintainability(self, analyzer, tmp_path):
        """Test maintainability of simple file."""
        code = tmp_path / "simple.py"
        code.write_text("x = 1\n")

        result = analyzer._analyze_maintainability([str(code)])

        assert isinstance(result, list)

    def test_complex_file_maintainability(self, analyzer, tmp_path):
        """Test maintainability of complex file."""
        code = tmp_path / "complex.py"
        # Write a moderately complex file
        lines = [
            "def func1(): return 1",
            "def func2(): return 2",
            "def func3(): return 3",
        ]
        code.write_text("\n".join(lines))

        result = analyzer._analyze_maintainability([str(code)])

        assert isinstance(result, list)

    def test_nonexistent_file_maintainability(self, analyzer, tmp_path):
        """Test handling nonexistent file."""
        result = analyzer._analyze_maintainability([str(tmp_path / "nonexistent.py")])

        # Should handle gracefully, returning empty or skipping
        assert isinstance(result, list)


class TestErrorHandling:
    """Tests for error handling in complexity analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, complexity_logger):
        """Create a ComplexityAnalyzer instance."""
        return ComplexityAnalyzer(
            repo_path=tmp_path,
            logger=complexity_logger,
            config={},
        )

    def test_parse_error_handling(self, analyzer, tmp_path):
        """Test handling of syntax errors in files."""
        code = tmp_path / "syntax_error.py"
        code.write_text("def broken(:\n    pass")  # Syntax error

        # Should not raise, should handle gracefully
        result = analyzer.analyze([str(code)])

        assert isinstance(result, ComplexityResults)
        assert isinstance(result.complexity, list)
        assert isinstance(result.maintainability, list)

    def test_binary_file_handling(self, analyzer, tmp_path):
        """Test handling of binary files."""
        binary = tmp_path / "binary.py"
        binary.write_bytes(b"\x00\x01\x02\x03")

        # Should not raise, should handle gracefully
        result = analyzer.analyze([str(binary)])

        assert isinstance(result, ComplexityResults)
