"""Tests for TestSuiteAnalyzer."""

import logging

import pytest

from glintefy.subservers.review.quality.analyzer_results import SuiteResults
from glintefy.subservers.review.quality.tests import TestSuiteAnalyzer


@pytest.fixture
def test_logger():
    """Create a logger for tests."""
    return logging.getLogger("test_tests")


class TestTestAnalyzerBasic:
    """Tests for TestAnalyzer class."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert isinstance(result, SuiteResults)
        assert result.test_files == []
        assert result.total_tests == 0
        assert result.total_assertions == 0
        assert result.issues == []

    def test_analyze_nonexistent_files(self, analyzer):
        """Test analyze with nonexistent files."""
        result = analyzer.analyze(["/nonexistent/test_file.py"])

        assert result.test_files == []
        assert result.total_tests == 0


class TestIdentifyTestFiles:
    """Tests for test file identification."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_identify_test_prefix(self, analyzer, tmp_path):
        """Test files starting with test_ are identified."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("x = 1")

        result = analyzer._identify_test_files([str(test_file)])

        assert str(test_file) in result

    def test_identify_test_suffix(self, analyzer, tmp_path):
        """Test files ending with _test.py are identified."""
        test_file = tmp_path / "example_test.py"
        test_file.write_text("x = 1")

        result = analyzer._identify_test_files([str(test_file)])

        assert str(test_file) in result

    def test_identify_conftest(self, analyzer, tmp_path):
        """Test conftest.py is identified as test file."""
        test_file = tmp_path / "conftest.py"
        test_file.write_text("x = 1")

        result = analyzer._identify_test_files([str(test_file)])

        assert str(test_file) in result

    def test_identify_tests_directory(self, analyzer, tmp_path):
        """Test files in tests/ directory are identified."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "module.py"
        test_file.write_text("x = 1")

        result = analyzer._identify_test_files([str(test_file)])

        assert str(test_file) in result

    def test_non_test_file_excluded(self, analyzer, tmp_path):
        """Test non-test files are excluded."""
        regular_file = tmp_path / "module.py"
        regular_file.write_text("x = 1")

        result = analyzer._identify_test_files([str(regular_file)])

        assert str(regular_file) not in result


class TestAssertionCounting:
    """Tests for assertion counting."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_count_assert_statements(self, analyzer, tmp_path):
        """Test counting assert statements."""
        test_file = tmp_path / "test_assertions.py"
        test_file.write_text('''
def test_with_asserts():
    """Test with assert statements."""
    x = 1
    assert x == 1
    assert x > 0
    assert isinstance(x, int)
''')

        result = analyzer.analyze([str(test_file)])

        assert result.total_tests == 1
        assert result.total_assertions == 3

    def test_count_no_assertions(self, analyzer, tmp_path):
        """Test counting when no assertions present."""
        test_file = tmp_path / "test_no_assert.py"
        test_file.write_text('''
def test_without_assertions():
    """Test without assertions."""
    x = 1 + 1
    y = x * 2
''')

        result = analyzer.analyze([str(test_file)])

        assert result.total_tests == 1
        assert result.total_assertions == 0
        # Should have a NO_ASSERTIONS issue
        assert any(i.type == "NO_ASSERTIONS" for i in result.issues)


class TestTestCategorization:
    """Tests for test file categorization."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_categorize_unit_test(self, analyzer, tmp_path):
        """Test unit test categorization."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        test_file = unit_dir / "test_unit.py"
        test_file.write_text("""
def test_unit():
    assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert result.categories.unit == 1

    def test_categorize_integration_test(self, analyzer, tmp_path):
        """Test integration test categorization."""
        int_dir = tmp_path / "integration"
        int_dir.mkdir()
        test_file = int_dir / "test_integration.py"
        test_file.write_text("""
def test_integration():
    assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert result.categories.integration == 1

    def test_categorize_e2e_test(self, analyzer, tmp_path):
        """Test e2e test categorization."""
        e2e_dir = tmp_path / "e2e"
        e2e_dir.mkdir()
        test_file = e2e_dir / "test_e2e.py"
        test_file.write_text("""
def test_end_to_end():
    assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert result.categories.e2e == 1

    def test_categorize_unknown(self, analyzer, tmp_path):
        """Test unknown category for uncategorized tests."""
        test_file = tmp_path / "test_unknown.py"
        test_file.write_text("""
def test_something():
    assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert result.categories.unknown == 1


class TestIssueDetection:
    """Tests for test issue detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_detect_no_assertions(self, analyzer, tmp_path):
        """Test detecting tests without assertions."""
        test_file = tmp_path / "test_no_assert.py"
        test_file.write_text("""
def test_without_assertion():
    x = 1
    y = 2
""")

        result = analyzer.analyze([str(test_file)])

        assert len(result.issues) >= 1
        assert any(i.type == "NO_ASSERTIONS" for i in result.issues)

    def test_detect_long_test(self, analyzer, tmp_path):
        """Test detecting long tests."""
        test_file = tmp_path / "test_long.py"
        # Create a test longer than 50 lines
        lines = ["def test_very_long():"]
        lines.append('    """Very long test."""')
        for i in range(55):
            lines.append(f"    x{i} = {i}")
        lines.append("    assert True")
        test_file.write_text("\n".join(lines))

        result = analyzer.analyze([str(test_file)])

        assert any(i.type == "LONG_TEST" for i in result.issues)


class TestOSSpecificDetection:
    """Tests for OS-specific code detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_detect_sys_platform_without_decorator(self, analyzer, tmp_path):
        """Test detecting sys.platform usage without skip decorator."""
        test_file = tmp_path / "test_os.py"
        test_file.write_text("""
import sys

def test_os_specific():
    if sys.platform == "linux":
        assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert any(i.type == "MISSING_OS_DECORATOR" for i in result.issues)

    def test_detect_os_name_without_decorator(self, analyzer, tmp_path):
        """Test detecting os.name usage without skip decorator."""
        test_file = tmp_path / "test_os_name.py"
        test_file.write_text("""
import os

def test_os_name():
    if os.name == "nt":
        assert True
""")

        result = analyzer.analyze([str(test_file)])

        assert any(i.type == "MISSING_OS_DECORATOR" for i in result.issues)

    def test_no_issue_with_skip_decorator(self, analyzer, tmp_path):
        """Test no issue when proper skip decorator is present."""
        test_file = tmp_path / "test_with_skip.py"
        test_file.write_text("""
import pytest
import sys

@pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
def test_linux_only():
    if sys.platform == "linux":
        assert True
""")

        result = analyzer.analyze([str(test_file)])

        # Should not have MISSING_OS_DECORATOR issue
        assert not any(i.type == "MISSING_OS_DECORATOR" for i in result.issues)


class TestDecoratorExtraction:
    """Tests for decorator name extraction."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_simple_decorator(self, analyzer, tmp_path):
        """Test extracting simple decorator name."""
        import ast

        code = "@skip\ndef test(): pass"
        tree = ast.parse(code)
        func = tree.body[0]

        name = analyzer._get_decorator_name(func.decorator_list[0])

        assert name == "skip"

    def test_attribute_decorator(self, analyzer, tmp_path):
        """Test extracting attribute decorator name."""
        import ast

        code = "@pytest.mark.skipif\ndef test(): pass"
        tree = ast.parse(code)
        func = tree.body[0]

        name = analyzer._get_decorator_name(func.decorator_list[0])

        assert "skipif" in name

    def test_call_decorator(self, analyzer, tmp_path):
        """Test extracting call decorator name."""
        import ast

        code = "@skip(reason='test')\ndef test(): pass"
        tree = ast.parse(code)
        func = tree.body[0]

        name = analyzer._get_decorator_name(func.decorator_list[0])

        assert name == "skip"


class TestAsyncTestSupport:
    """Tests for async test function support."""

    @pytest.fixture
    def analyzer(self, tmp_path, test_logger):
        """Create a TestAnalyzer instance."""
        return TestSuiteAnalyzer(
            repo_path=tmp_path,
            logger=test_logger,
            config={},
        )

    def test_async_test_counted(self, analyzer, tmp_path):
        """Test that async test functions are counted."""
        test_file = tmp_path / "test_async.py"
        test_file.write_text('''
async def test_async_function():
    """Async test function."""
    x = await some_async_call()
    assert x is not None
''')

        result = analyzer.analyze([str(test_file)])

        assert result.total_tests == 1
        assert result.total_assertions == 1
