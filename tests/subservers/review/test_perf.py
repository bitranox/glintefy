"""Tests for Perf sub-server."""

import pytest

from glintefy.subservers.review.perf import PerfSubServer


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


class TestNestedLoopThreshold:
    """Tests for nested_loop_threshold configuration."""

    def test_default_nested_loop_threshold(self, tmp_path):
        """Test that default nested_loop_threshold is 2."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        assert server.nested_loop_threshold == 2

    def test_nested_loops_below_threshold(self, tmp_path):
        """Test that single loop doesn't trigger warning with threshold 2."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        src_dir = project_dir / "src"
        src_dir.mkdir()

        # Single loop - should not trigger warning with threshold 2
        (src_dir / "single.py").write_text('''
def single_loop():
    """Single loop."""
    for i in range(100):
        print(i)
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("src/single.py")

        server = PerfSubServer(
            input_dir=scope_dir,
            output_dir=tmp_path / "output",
            repo_path=project_dir,
        )

        files = [str(project_dir / "src" / "single.py")]
        issues = server._analyze_complexity(files)

        # Should not find nested iteration issues for single loop
        nested_issues = [i for i in issues if i.type == "nested_iteration"]
        assert len(nested_issues) == 0

    def test_nested_loops_at_threshold(self, tmp_path):
        """Test that 2-level nesting triggers warning with threshold 2."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        src_dir = project_dir / "src"
        src_dir.mkdir()

        # 2-level nesting (nested loop)
        (src_dir / "double.py").write_text('''
def double_nested():
    """Double nested loop."""
    for i in range(10):
        for j in range(10):
            print(i, j)
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("src/double.py")

        server = PerfSubServer(
            input_dir=scope_dir,
            output_dir=tmp_path / "output",
            repo_path=project_dir,
        )

        files = [str(project_dir / "src" / "double.py")]
        issues = server._analyze_complexity(files)

        # Should find nested iteration issue (threshold 2, nesting level 2)
        nested_issues = [i for i in issues if i.type == "nested_iteration"]
        assert len(nested_issues) == 1
        assert "depth 2" in nested_issues[0].message

    def test_triple_nested_loops(self, tmp_path):
        """Test that 3-level nesting triggers warning with threshold 2."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        src_dir = project_dir / "src"
        src_dir.mkdir()

        # 3-level nesting
        (src_dir / "triple.py").write_text('''
def triple_nested():
    """Triple nested loop."""
    for i in range(5):
        for j in range(5):
            for k in range(5):
                print(i, j, k)
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("src/triple.py")

        server = PerfSubServer(
            input_dir=scope_dir,
            output_dir=tmp_path / "output",
            repo_path=project_dir,
        )

        files = [str(project_dir / "src" / "triple.py")]
        issues = server._analyze_complexity(files)

        # Should find 2 nested iteration issues (depth 2 and depth 3)
        nested_issues = [i for i in issues if i.type == "nested_iteration"]
        assert len(nested_issues) == 2
        messages = [i.message for i in nested_issues]
        assert any("depth 2" in msg for msg in messages)
        assert any("depth 3" in msg for msg in messages)

    def test_high_threshold_no_warning(self, tmp_path):
        """Test that high threshold (3) doesn't warn on 2-level nesting."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        src_dir = project_dir / "src"
        src_dir.mkdir()

        # 2-level nesting
        (src_dir / "double.py").write_text('''
def double_nested():
    """Double nested loop."""
    for i in range(10):
        for j in range(10):
            print(i, j)
''')

        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "files_code.txt").write_text("src/double.py")

        # Create server with custom threshold (via config search won't work in test)
        # Instead, verify programmatic override works
        server = PerfSubServer(
            input_dir=scope_dir,
            output_dir=tmp_path / "output",
            repo_path=project_dir,
        )

        # Manually set threshold for this test
        server.nested_loop_threshold = 3

        # Verify threshold is set
        assert server.nested_loop_threshold == 3

        files = [str(project_dir / "src" / "double.py")]
        issues = server._analyze_complexity(files)

        # Should NOT find nested iteration issues (threshold 3, nesting level 2)
        nested_issues = [i for i in issues if i.type == "nested_iteration"]
        assert len(nested_issues) == 0

    def test_threshold_settings_loaded(self, tmp_path):
        """Test that all threshold settings are loaded from config."""
        server = PerfSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        # Verify all thresholds are loaded
        assert server.nested_loop_threshold == 2
        assert server.runtime_threshold_ms == 100
        assert server.memory_threshold_mb == 50

        # Verify feature flags are loaded
        assert server.estimate_runtime is True
        assert server.estimate_memory is True
        assert server.detect_complexity is True
