"""Tests for Perf sub-server."""

import pytest

from btx_fix_mcp.subservers.review.perf import PerfSubServer


class TestPerfSubServer:
    """Tests for PerfSubServer class."""

    @pytest.fixture
    def project_with_code(self, tmp_path):
        """Create a project with Python code."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        src_dir = project_dir / "src"
        src_dir.mkdir()

        # Create file with performance patterns
        (src_dir / "slow.py").write_text('''
"""Module with performance issues."""

def nested_loops():
    """Function with nested loops."""
    for i in range(100):
        for j in range(100):
            print(i, j)

def inefficient_list():
    """Function with list in loop."""
    result = []
    for i in range(100):
        result = result + [i]  # Creates new list each time

def duplicate_calculation():
    """Function with duplicate calculations."""
    total = sum(range(1000)) + sum(range(1000))
    return total
''')

        # Create file without issues
        (src_dir / "fast.py").write_text('''
"""Efficient module."""

def efficient_function():
    """Well-optimized function."""
    return [i for i in range(100)]
''')

        return project_dir

    @pytest.fixture
    def scope_output(self, project_with_code, tmp_path):
        """Create scope output directory."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()

        (scope_dir / "files_code.txt").write_text("src/slow.py\nsrc/fast.py")

        return scope_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        server = PerfSubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        assert server.name == "perf"
        assert server.output_dir == output_dir
        assert server.repo_path == tmp_path
        assert server.run_profiling is True

    def test_initialization_custom_options(self, tmp_path):
        """Test initialization with custom options."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            run_profiling=False,
        )

        assert server.run_profiling is False

    def test_validate_inputs_no_files(self, tmp_path):
        """Test validation fails with no files list."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        server = PerfSubServer(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No files list" in m for m in missing)

    def test_validate_inputs_with_files(self, scope_output, tmp_path):
        """Test validation passes with files list."""
        server = PerfSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_detect_patterns(self, project_with_code, tmp_path):
        """Test pattern detection."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=project_with_code,
        )

        files = [str(project_with_code / "src" / "slow.py")]
        issues = server._detect_patterns(files)

        # Should find nested loop pattern (type field contains the pattern name)
        issue_types = [i.type for i in issues]
        assert "nested_loop" in issue_types

    def test_execute_with_code(self, project_with_code, scope_output, tmp_path):
        """Test execution with code files."""
        server = PerfSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=project_with_code,
            run_profiling=False,  # Skip profiling in tests
        )

        result = server.run()

        assert result.status in ("SUCCESS", "PARTIAL")
        assert "Performance Analysis" in result.summary
        assert result.metrics.get("files_analyzed", 0) >= 0

    def test_expensive_patterns_defined(self, tmp_path):
        """Test that expensive patterns are defined."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        assert len(server.EXPENSIVE_PATTERNS) > 0
        # Check pattern structure
        for pattern, name, description in server.EXPENSIVE_PATTERNS:
            assert isinstance(pattern, str)
            assert isinstance(name, str)
            assert isinstance(description, str)

    def test_mindset_loaded(self, tmp_path):
        """Test that perf mindset is loaded."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        assert server.mindset is not None
        assert server.mindset.name == "perf"

    def test_summary_includes_mindset(self, project_with_code, scope_output, tmp_path):
        """Test that summary includes mindset information."""
        server = PerfSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=project_with_code,
            run_profiling=False,
        )

        result = server.run()

        assert "Reviewer Mindset" in result.summary
        assert "Verdict" in result.summary


class TestPerfSubServerMCPMode:
    """Tests for PerfSubServer in MCP mode."""

    def test_mcp_mode_enabled(self, tmp_path):
        """Test that MCP mode can be enabled."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            mcp_mode=True,
        )

        assert server.mcp_mode is True
        assert server.logger is not None
