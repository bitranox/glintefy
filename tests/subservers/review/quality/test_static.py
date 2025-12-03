"""Tests for StaticAnalyzer."""

import json
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from glintefy.subservers.review.quality.analyzer_results import RuffDiagnostic, StaticResults
from glintefy.subservers.review.quality.static import StaticAnalyzer


@pytest.fixture
def static_logger():
    """Create a logger for tests."""
    return logging.getLogger("test_static")


class TestStaticAnalyzerBasic:
    """Tests for StaticAnalyzer class."""

    @pytest.fixture
    def analyzer(self, tmp_path, static_logger):
        """Create a StaticAnalyzer instance."""
        return StaticAnalyzer(
            repo_path=tmp_path,
            logger=static_logger,
            config={},
        )

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert isinstance(result, StaticResults)
        assert result.static.ruff == ""
        assert result.duplication.duplicates == []

    def test_analyze_returns_static_results(self, analyzer, tmp_path):
        """Test analyze returns StaticResults dataclass."""
        code = tmp_path / "simple.py"
        code.write_text("x = 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            result = analyzer.analyze([str(code)])

        assert isinstance(result, StaticResults)
        assert isinstance(result.static.ruff_json, list)


class TestRunRuff:
    """Tests for _run_ruff method."""

    @pytest.fixture
    def analyzer(self, tmp_path, static_logger):
        """Create a StaticAnalyzer instance."""
        return StaticAnalyzer(
            repo_path=tmp_path,
            logger=static_logger,
            config={},
        )

    def test_run_ruff_success(self, analyzer, tmp_path):
        """Test successful Ruff run."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = json.dumps([{"code": "E501", "message": "Line too long"}])

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._run_ruff([str(code)])

        assert len(result.ruff_json) == 1
        assert isinstance(result.ruff_json[0], RuffDiagnostic)
        assert result.ruff_json[0].code == "E501"
        assert result.ruff_json[0].message == "Line too long"

    def test_run_ruff_empty_output(self, analyzer, tmp_path):
        """Test Ruff with empty output."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._run_ruff([str(code)])

        assert result.ruff == ""
        assert result.ruff_json == []

    def test_run_ruff_invalid_json(self, analyzer, tmp_path):
        """Test Ruff with invalid JSON output."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = "not valid json"

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._run_ruff([str(code)])

        assert result.ruff == "not valid json"
        assert result.ruff_json == []

    def test_run_ruff_timeout(self, analyzer, tmp_path):
        """Test Ruff timeout handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 60)):
            result = analyzer._run_ruff([str(code)])

        assert result.ruff == ""
        assert result.ruff_json == []

    def test_run_ruff_not_found(self, analyzer, tmp_path):
        """Test Ruff not found handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = analyzer._run_ruff([str(code)])

        assert result.ruff == ""
        assert result.ruff_json == []

    def test_run_ruff_other_error(self, analyzer, tmp_path):
        """Test Ruff other error handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=Exception("unexpected error")):
            result = analyzer._run_ruff([str(code)])

        assert result.ruff == ""
        assert result.ruff_json == []


class TestDetectDuplication:
    """Tests for _detect_duplication method."""

    @pytest.fixture
    def analyzer(self, tmp_path, static_logger):
        """Create a StaticAnalyzer instance."""
        return StaticAnalyzer(
            repo_path=tmp_path,
            logger=static_logger,
            config={},
        )

    def test_detect_duplication_success(self, analyzer, tmp_path):
        """Test successful duplication detection."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = "test.py:1: Similar lines found\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._detect_duplication([str(code)])

        assert len(result.duplicates) >= 1

    def test_detect_duplication_no_duplicates(self, analyzer, tmp_path):
        """Test no duplicates found."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = "No duplicates found\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._detect_duplication([str(code)])

        assert result.duplicates == []

    def test_detect_duplication_timeout(self, analyzer, tmp_path):
        """Test duplication detection timeout."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pylint", 120)):
            result = analyzer._detect_duplication([str(code)])

        assert result.duplicates == []

    def test_detect_duplication_not_found(self, analyzer, tmp_path):
        """Test pylint not found."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = analyzer._detect_duplication([str(code)])

        assert result.duplicates == []

    def test_detect_duplication_other_error(self, analyzer, tmp_path):
        """Test other error handling."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        with patch("subprocess.run", side_effect=Exception("unexpected error")):
            result = analyzer._detect_duplication([str(code)])

        assert result.duplicates == []

    def test_detect_duplicate_code_line(self, analyzer, tmp_path):
        """Test detecting lines with duplicate-code."""
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        mock_result = MagicMock()
        mock_result.stdout = "R0801: duplicate-code detected\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = analyzer._detect_duplication([str(code)])

        assert len(result.duplicates) == 1
        assert "duplicate-code" in result.duplicates[0]
