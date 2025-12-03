"""Tests for TypeAnalyzer."""

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from glintefy.subservers.common.issues import DocstringCoverageMetrics, TypeCoverageMetrics
from glintefy.subservers.review.quality.analyzer_results import TypeResults
from glintefy.subservers.review.quality.types import TypeAnalyzer


@pytest.fixture
def type_logger():
    """Create a logger for tests."""
    return logging.getLogger("test_types")


class TestTypeAnalyzerBasic:
    """Basic tests for TypeAnalyzer."""

    @pytest.fixture
    def analyzer(self, tmp_path, type_logger):
        """Create a TypeAnalyzer instance."""
        return TypeAnalyzer(
            repo_path=tmp_path,
            logger=type_logger,
            config={},
        )

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert isinstance(result, TypeResults)
        assert result.type_coverage.coverage_percent == 0
        assert result.dead_code.dead_code == []
        assert result.docstring_coverage.coverage_percent == 0

    def test_analyze_returns_type_results(self, analyzer, tmp_path):
        """Test analyze returns TypeResults dataclass."""
        code = tmp_path / "simple.py"
        code.write_text("x = 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            result = analyzer.analyze([str(code)])

        assert isinstance(result, TypeResults)
        assert isinstance(result.type_coverage, TypeCoverageMetrics)
        assert isinstance(result.docstring_coverage, DocstringCoverageMetrics)


class TestAnalyzeTypeCoverage:
    """Tests for _analyze_type_coverage method."""

    @pytest.fixture
    def analyzer(self, tmp_path, type_logger):
        """Create a TypeAnalyzer instance."""
        return TypeAnalyzer(
            repo_path=tmp_path,
            logger=type_logger,
            config={},
        )

    def test_type_coverage_empty_files(self, analyzer):
        """Test type coverage with empty file list."""
        result = analyzer._analyze_type_coverage([])
        assert result.coverage_percent == 0
        assert result.typed_functions == 0

    def test_type_coverage_success(self, analyzer, tmp_path):
        """Test successful type coverage analysis."""
        code = tmp_path / "test.py"
        code.write_text("def foo(): pass")

        mock_result = MagicMock()
        mock_result.stdout = "note: def foo() -> int\nnote: def bar()\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._analyze_type_coverage([str(code)])

        assert result.typed_functions == 1
        assert result.untyped_functions == 1
        assert result.coverage_percent == 50.0

    def test_type_coverage_all_typed(self, analyzer, tmp_path):
        """Test 100% type coverage."""
        code = tmp_path / "test.py"
        code.write_text("def foo() -> int: return 1")

        mock_result = MagicMock()
        mock_result.stdout = "note: def foo() -> int\nnote: def bar() -> str\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._analyze_type_coverage([str(code)])

        assert result.typed_functions == 2
        assert result.untyped_functions == 0
        assert result.coverage_percent == 100.0

    def test_type_coverage_with_errors(self, analyzer, tmp_path):
        """Test type coverage capturing errors."""
        code = tmp_path / "test.py"
        code.write_text("x: int = 'string'")

        mock_result = MagicMock()
        mock_result.stdout = "test.py:1: error: incompatible type\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._analyze_type_coverage([str(code)])

        assert len(result.errors) == 1
        assert "incompatible type" in result.errors[0]

    def test_type_coverage_timeout(self, analyzer, tmp_path):
        """Test type coverage timeout handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("mypy", 120)):
            result = analyzer._analyze_type_coverage([str(code)])

        assert result.coverage_percent == 0

    def test_type_coverage_not_found(self, analyzer, tmp_path):
        """Test type coverage when mypy not found."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = analyzer._analyze_type_coverage([str(code)])

        assert result.coverage_percent == 0

    def test_type_coverage_other_error(self, analyzer, tmp_path):
        """Test type coverage other error handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=Exception("unexpected error")):
            result = analyzer._analyze_type_coverage([str(code)])

        assert result.coverage_percent == 0


class TestDetectDeadCode:
    """Tests for _detect_dead_code method."""

    @pytest.fixture
    def analyzer(self, tmp_path, type_logger):
        """Create a TypeAnalyzer instance."""
        return TypeAnalyzer(
            repo_path=tmp_path,
            logger=type_logger,
            config={"dead_code_confidence": 80},
        )

    def test_dead_code_empty_files(self, analyzer):
        """Test dead code detection with empty file list."""
        result = analyzer._detect_dead_code([])
        assert result.dead_code == []

    def test_dead_code_found(self, analyzer, tmp_path):
        """Test detecting dead code."""
        code = tmp_path / "test.py"
        code.write_text("def unused_func(): pass")

        mock_result = MagicMock()
        mock_result.stdout = f"{code}:1: unused function 'unused_func' (80% confidence)\n"

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._detect_dead_code([str(code)])

        assert len(result.dead_code) == 1
        assert result.dead_code[0].line == 1
        assert "unused" in result.dead_code[0].message

    def test_dead_code_no_results(self, analyzer, tmp_path):
        """Test no dead code found."""
        code = tmp_path / "test.py"
        code.write_text("print('hello')")

        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._detect_dead_code([str(code)])

        assert result.dead_code == []

    def test_dead_code_timeout(self, analyzer, tmp_path):
        """Test dead code detection timeout."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("vulture", 60)):
            result = analyzer._detect_dead_code([str(code)])

        assert result.dead_code == []

    def test_dead_code_not_found(self, analyzer, tmp_path):
        """Test vulture not found."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = analyzer._detect_dead_code([str(code)])

        assert result.dead_code == []

    def test_dead_code_other_error(self, analyzer, tmp_path):
        """Test other error handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=Exception("unexpected error")):
            result = analyzer._detect_dead_code([str(code)])

        assert result.dead_code == []


class TestAnalyzeDocstringCoverage:
    """Tests for _analyze_docstring_coverage method."""

    @pytest.fixture
    def analyzer(self, tmp_path, type_logger):
        """Create a TypeAnalyzer instance."""
        return TypeAnalyzer(
            repo_path=tmp_path,
            logger=type_logger,
            config={},
        )

    def test_docstring_coverage_empty_files(self, analyzer):
        """Test docstring coverage with empty file list."""
        result = analyzer._analyze_docstring_coverage([])
        assert result.coverage_percent == 0
        assert result.missing == []

    def test_docstring_coverage_success(self, analyzer, tmp_path):
        """Test successful docstring coverage analysis."""
        code = tmp_path / "test.py"
        code.write_text('def foo():\n    """Docstring."""\n    pass')

        mock_result = MagicMock()
        mock_result.stdout = "PASSED (80.5%)\n"

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._analyze_docstring_coverage([str(code)])

        assert result.coverage_percent == 80.5

    def test_docstring_coverage_failed(self, analyzer, tmp_path):
        """Test docstring coverage with low coverage."""
        code = tmp_path / "test.py"
        code.write_text("def foo(): pass")

        mock_result = MagicMock()
        mock_result.stdout = "FAILED (20%)\nmissing docstring for foo\n"

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._analyze_docstring_coverage([str(code)])

        assert result.coverage_percent == 20.0
        assert len(result.missing) >= 1

    def test_docstring_coverage_timeout(self, analyzer, tmp_path):
        """Test docstring coverage timeout."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("interrogate", 60)):
            result = analyzer._analyze_docstring_coverage([str(code)])

        assert result.coverage_percent == 0

    def test_docstring_coverage_not_found(self, analyzer, tmp_path):
        """Test interrogate not found."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = analyzer._analyze_docstring_coverage([str(code)])

        assert result.coverage_percent == 0

    def test_docstring_coverage_other_error(self, analyzer, tmp_path):
        """Test other error handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=Exception("unexpected error")):
            result = analyzer._analyze_docstring_coverage([str(code)])

        assert result.coverage_percent == 0
