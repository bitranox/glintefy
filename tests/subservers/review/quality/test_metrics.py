"""Tests for MetricsAnalyzer."""

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from glintefy.subservers.review.quality.analyzer_results import MetricsResults
from glintefy.subservers.review.quality.metrics import MetricsAnalyzer


@pytest.fixture
def logger():
    """Create a logger for tests."""
    return logging.getLogger("test_metrics")


class TestMetricsAnalyzer:
    """Tests for MetricsAnalyzer class."""

    @pytest.fixture
    def analyzer(self, tmp_path, logger):
        """Create a MetricsAnalyzer instance."""
        return MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )

    @pytest.fixture
    def python_file(self, tmp_path):
        """Create a Python file for testing."""
        code = tmp_path / "test_code.py"
        code.write_text('''
def example():
    """Example function."""
    x = 1
    y = 2
    return x + y
''')
        return str(code)

    def test_analyze_returns_metrics_results(self, analyzer, python_file):
        """Test analyze returns MetricsResults dataclass."""
        result = analyzer.analyze([python_file])

        assert isinstance(result, MetricsResults)
        assert isinstance(result.halstead, list)
        assert isinstance(result.raw_metrics, list)

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert result.halstead == []
        assert result.raw_metrics == []
        assert result.code_churn.files == []

    def test_analyze_nonexistent_files(self, analyzer):
        """Test analyze with nonexistent files."""
        result = analyzer.analyze(["/nonexistent/file.py"])

        assert result.halstead == []
        assert result.raw_metrics == []


class TestHalsteadAnalysis:
    """Tests for Halstead metrics analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, logger):
        """Create a MetricsAnalyzer instance."""
        return MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )

    @pytest.fixture
    def python_file(self, tmp_path):
        """Create a Python file with enough complexity for Halstead."""
        code = tmp_path / "complex.py"
        code.write_text('''
def calculate(a, b, c):
    """Calculate something complex."""
    if a > 0:
        result = a + b * c
    else:
        result = b - c
    return result + a

def another(x, y):
    """Another function."""
    return x * y + x - y
''')
        return str(code)

    def test_halstead_metrics_structure(self, analyzer, python_file):
        """Test Halstead metrics returns HalsteadItem dataclasses."""
        result = analyzer._analyze_halstead([python_file])

        # If radon is installed and works, verify structure
        if result:
            assert isinstance(result, list)
            for item in result:
                # HalsteadItem dataclass has fixed fields
                assert item.file
                assert isinstance(item.vocabulary, int)

    def test_halstead_timeout_handling(self, analyzer, python_file):
        """Test timeout is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("radon", 30)

            result = analyzer._analyze_halstead([python_file])

            assert result == []

    def test_halstead_json_decode_error(self, analyzer, python_file):
        """Test invalid JSON is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not valid json")

            result = analyzer._analyze_halstead([python_file])

            assert result == []

    def test_halstead_radon_not_found(self, analyzer, python_file):
        """Test missing radon is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = analyzer._analyze_halstead([python_file])

            assert result == []


class TestRawMetricsAnalysis:
    """Tests for raw metrics analysis."""

    @pytest.fixture
    def analyzer(self, tmp_path, logger):
        """Create a MetricsAnalyzer instance."""
        return MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )

    @pytest.fixture
    def python_file(self, tmp_path):
        """Create a Python file for testing."""
        code = tmp_path / "raw.py"
        code.write_text('''"""Module docstring."""

# Single line comment
def foo():
    """Function docstring."""
    x = 1
    y = 2
    return x + y


def bar():
    pass
''')
        return str(code)

    def test_raw_metrics_structure(self, analyzer, python_file):
        """Test raw metrics returns RawMetricsItem dataclasses."""
        result = analyzer._analyze_raw_metrics([python_file])

        # If radon is installed and works, verify structure
        if result:
            assert isinstance(result, list)
            for item in result:
                # RawMetricsItem dataclass has fixed fields
                assert item.file
                assert isinstance(item.loc, int)

    def test_raw_metrics_timeout_handling(self, analyzer, python_file):
        """Test timeout is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("radon", 30)

            result = analyzer._analyze_raw_metrics([python_file])

            assert result == []

    def test_raw_metrics_json_decode_error(self, analyzer, python_file):
        """Test invalid JSON is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not valid json")

            result = analyzer._analyze_raw_metrics([python_file])

            assert result == []

    def test_raw_metrics_radon_not_found(self, analyzer, python_file):
        """Test missing radon is handled gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = analyzer._analyze_raw_metrics([python_file])

            assert result == []


class TestCodeChurnAnalysis:
    """Tests for code churn analysis."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a git repository for testing."""
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        # Create a file and commit it
        code = tmp_path / "churn.py"
        code.write_text("x = 1")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        return tmp_path

    @pytest.fixture
    def analyzer(self, git_repo, logger):
        """Create a MetricsAnalyzer with git repo."""
        return MetricsAnalyzer(
            repo_path=git_repo,
            logger=logger,
            config={"churn_threshold": 20},
        )

    def test_churn_in_git_repo(self, analyzer, git_repo):
        """Test churn analysis in a git repository."""
        code_file = git_repo / "churn.py"
        result = analyzer._analyze_code_churn([str(code_file)])

        # CodeChurnResults dataclass with fixed fields
        assert isinstance(result.files, list)
        assert isinstance(result.high_churn_files, list)
        assert isinstance(result.total_commits_analyzed, int)
        assert isinstance(result.analysis_period_days, int)

    def test_churn_empty_files(self, analyzer):
        """Test churn with empty file list."""
        result = analyzer._analyze_code_churn([])

        assert result.files == []
        assert result.total_commits_analyzed == 0

    def test_churn_not_git_repo(self, tmp_path, logger):
        """Test churn analysis in non-git directory."""
        analyzer = MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )
        code = tmp_path / "test.py"
        code.write_text("x = 1")

        result = analyzer._analyze_code_churn([str(code)])

        # Should return empty results, not error
        assert result.files == []

    def test_churn_handles_git_timeout(self, analyzer, git_repo):
        """Test churn handles git timeout gracefully."""
        with patch("subprocess.run") as mock_run:
            # First call (git rev-parse) succeeds, second (git log) times out
            mock_run.side_effect = [
                MagicMock(returncode=0),
                subprocess.TimeoutExpired("git", 60),
            ]

            code_file = git_repo / "churn.py"
            result = analyzer._analyze_code_churn([str(code_file)])

            assert result.files == []

    def test_churn_handles_git_not_found(self, tmp_path, logger):
        """Test churn handles missing git gracefully."""
        analyzer = MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = analyzer._analyze_code_churn(["/tmp/test.py"])

            assert result.files == []


class TestMetricsIntegration:
    """Integration tests for MetricsAnalyzer."""

    def test_full_analysis_workflow(self, tmp_path, logger):
        """Test complete metrics analysis workflow."""
        # Create code file
        code = tmp_path / "sample.py"
        code.write_text('''
"""Sample module."""

def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    result = x * y
    return result
''')

        analyzer = MetricsAnalyzer(
            repo_path=tmp_path,
            logger=logger,
            config={},
        )

        result = analyzer.analyze([str(code)])

        # Should complete without errors and return MetricsResults
        assert isinstance(result, MetricsResults)
        assert isinstance(result.halstead, list)
        assert isinstance(result.raw_metrics, list)
