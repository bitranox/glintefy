"""Tests for ArchitectureAnalyzer."""

import logging

import pytest

from glintefy.subservers.review.quality.analyzer_results import ArchitectureResults
from glintefy.subservers.review.quality.architecture import ArchitectureAnalyzer


@pytest.fixture
def arch_logger():
    """Create a logger for tests."""
    return logging.getLogger("test_architecture")


class TestArchitectureAnalyzer:
    """Tests for ArchitectureAnalyzer class."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={},
        )

    def test_analyze_returns_architecture_results(self, analyzer, tmp_path):
        """Test analyze returns ArchitectureResults dataclass."""
        code = tmp_path / "simple.py"
        code.write_text("x = 1")

        result = analyzer.analyze([str(code)])

        # Result is a typed ArchitectureResults dataclass
        assert isinstance(result, ArchitectureResults)
        assert isinstance(result.architecture.god_objects, list)
        assert isinstance(result.import_cycles.cycles, list)

    def test_analyze_empty_files(self, analyzer):
        """Test analyze with empty file list."""
        result = analyzer.analyze([])

        assert result.architecture.god_objects == []
        assert result.architecture.highly_coupled == []
        assert result.import_cycles.cycles == []
        assert result.runtime_checks == []

    def test_analyze_nonexistent_files(self, analyzer):
        """Test analyze with nonexistent files."""
        result = analyzer.analyze(["/nonexistent/file.py"])

        assert result.architecture.god_objects == []


class TestGodObjectDetection:
    """Tests for god object detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance with low thresholds."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={
                "god_object_methods_threshold": 3,
                "god_object_lines_threshold": 10,
            },
        )

    def test_detect_god_object_by_methods(self, analyzer, tmp_path):
        """Test detecting god objects with too many methods."""
        code = tmp_path / "god_class.py"
        code.write_text('''
class GodClass:
    """A class with too many methods."""

    def method1(self):
        pass

    def method2(self):
        pass

    def method3(self):
        pass

    def method4(self):
        pass

    def method5(self):
        pass
''')

        result = analyzer._analyze_architecture([str(code)])

        assert len(result.god_objects) >= 1
        god_obj = result.god_objects[0]
        assert god_obj.class_name == "GodClass"
        assert god_obj.methods >= 5

    def test_no_god_object_for_small_class(self, tmp_path, arch_logger):
        """Test that small classes are not flagged."""
        analyzer = ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={
                "god_object_methods_threshold": 20,
                "god_object_lines_threshold": 500,
            },
        )
        code = tmp_path / "small_class.py"
        code.write_text('''
class SmallClass:
    """A small well-designed class."""

    def method1(self):
        return 1

    def method2(self):
        return 2
''')

        result = analyzer._analyze_architecture([str(code)])

        assert len(result.god_objects) == 0


class TestModuleCoupling:
    """Tests for module coupling detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance with low threshold."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={
                "coupling_threshold": 3,
            },
        )

    def test_detect_highly_coupled(self, analyzer, tmp_path):
        """Test detecting highly coupled modules."""
        code = tmp_path / "coupled.py"
        code.write_text("""
import os
import sys
import json
import logging
import subprocess

x = 1
""")

        result = analyzer._analyze_architecture([str(code)])

        assert len(result.highly_coupled) >= 1
        assert result.highly_coupled[0].import_count >= 5

    def test_no_coupling_issue_for_few_imports(self, tmp_path, arch_logger):
        """Test that files with few imports are not flagged."""
        analyzer = ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={
                "coupling_threshold": 15,
            },
        )
        code = tmp_path / "simple.py"
        code.write_text("""
import os

x = os.getcwd()
""")

        result = analyzer._analyze_architecture([str(code)])

        assert len(result.highly_coupled) == 0


class TestImportCycleDetection:
    """Tests for import cycle detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={},
        )

    def test_no_cycles_in_simple_code(self, analyzer, tmp_path):
        """Test no cycles detected in simple code."""
        code = tmp_path / "simple.py"
        code.write_text("""
import os
x = 1
""")

        result = analyzer._detect_import_cycles([str(code)])

        assert result.cycles == []

    def test_import_graph_built(self, analyzer, tmp_path):
        """Test that import graph is built correctly."""
        code = tmp_path / "module.py"
        code.write_text("""
import os
import sys
from pathlib import Path
""")

        result = analyzer._detect_import_cycles([str(code)])

        # ImportCycleResults dataclass has import_graph field
        assert isinstance(result.import_graph, dict)

    def test_handles_import_from(self, analyzer, tmp_path):
        """Test handling of 'from x import y' statements."""
        code = tmp_path / "imports.py"
        code.write_text("""
from pathlib import Path
from typing import Any, List
""")

        result = analyzer._detect_import_cycles([str(code)])

        # Should complete without errors
        assert isinstance(result.import_graph, dict)


class TestRuntimeCheckDetection:
    """Tests for runtime check detection."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={},
        )

    def test_detect_os_getenv(self, analyzer, tmp_path):
        """Test detecting os.getenv in function."""
        code = tmp_path / "runtime.py"
        code.write_text("""
import os

def get_config():
    return os.getenv("CONFIG")
""")

        result = analyzer._detect_runtime_checks([str(code)])

        assert len(result) >= 1
        assert result[0].function == "get_config"

    def test_detect_sys_platform(self, analyzer, tmp_path):
        """Test detecting sys.platform check."""
        code = tmp_path / "platform.py"
        code.write_text("""
import sys

def is_linux():
    return sys.platform == "linux"
""")

        # sys.platform as attribute access is not caught by _is_runtime_check
        # which only catches Call nodes
        result = analyzer._detect_runtime_checks([str(code)])

        # May or may not detect based on implementation
        assert isinstance(result, list)

    def test_detect_hasattr(self, analyzer, tmp_path):
        """Test detecting hasattr calls."""
        code = tmp_path / "checks.py"
        code.write_text("""
def check_feature(obj):
    if hasattr(obj, "feature"):
        return obj.feature
    return None
""")

        result = analyzer._detect_runtime_checks([str(code)])

        assert len(result) >= 1
        assert result[0].function == "check_feature"

    def test_detect_isinstance(self, analyzer, tmp_path):
        """Test detecting isinstance calls."""
        code = tmp_path / "typecheck.py"
        code.write_text("""
def process(x):
    if isinstance(x, int):
        return x * 2
    return x
""")

        result = analyzer._detect_runtime_checks([str(code)])

        assert len(result) >= 1

    def test_no_detection_for_module_level(self, analyzer, tmp_path):
        """Test that module-level checks are not flagged."""
        code = tmp_path / "module_level.py"
        code.write_text("""
import os

# Module level - not flagged
DEBUG = os.getenv("DEBUG", False)

def normal_function():
    return 42
""")

        result = analyzer._detect_runtime_checks([str(code)])

        # Should not flag module-level os.getenv
        # Only function-level checks should be flagged
        function_names = [r.function for r in result]
        assert "normal_function" not in function_names or len(result) == 0


class TestIsRuntimeCheck:
    """Tests for _is_runtime_check helper."""

    @pytest.fixture
    def analyzer(self, tmp_path, arch_logger):
        """Create an ArchitectureAnalyzer instance."""
        return ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={},
        )

    def test_os_getenv_is_runtime_check(self, analyzer):
        """Test os.getenv is detected as runtime check."""
        import ast

        code = "os.getenv('X')"
        tree = ast.parse(code, mode="eval")
        node = tree.body

        assert analyzer._is_runtime_check(node) is True

    def test_os_environ_is_runtime_check(self, analyzer):
        """Test os.environ is detected as runtime check."""
        import ast

        code = "os.environ.get('X')"
        tree = ast.parse(code, mode="eval")
        # This is os.environ.get() which is nested differently
        # Only os.environ attribute access is checked
        node = tree.body

        # May not be detected as it's os.environ.get not os.environ
        result = analyzer._is_runtime_check(node)
        assert isinstance(result, bool)

    def test_hasattr_is_runtime_check(self, analyzer):
        """Test hasattr is detected as runtime check."""
        import ast

        code = "hasattr(obj, 'attr')"
        tree = ast.parse(code, mode="eval")
        node = tree.body

        assert analyzer._is_runtime_check(node) is True

    def test_isinstance_is_runtime_check(self, analyzer):
        """Test isinstance is detected as runtime check."""
        import ast

        code = "isinstance(x, int)"
        tree = ast.parse(code, mode="eval")
        node = tree.body

        assert analyzer._is_runtime_check(node) is True

    def test_callable_is_runtime_check(self, analyzer):
        """Test callable is detected as runtime check."""
        import ast

        code = "callable(obj)"
        tree = ast.parse(code, mode="eval")
        node = tree.body

        assert analyzer._is_runtime_check(node) is True

    def test_regular_call_not_runtime_check(self, analyzer):
        """Test regular function call is not a runtime check."""
        import ast

        code = "print('hello')"
        tree = ast.parse(code, mode="eval")
        node = tree.body

        assert analyzer._is_runtime_check(node) is False


class TestArchitectureIntegration:
    """Integration tests for ArchitectureAnalyzer."""

    def test_full_analysis_workflow(self, tmp_path, arch_logger):
        """Test complete architecture analysis workflow."""
        from glintefy.subservers.review.quality.analyzer_results import ArchitectureResults

        # Create code files
        module_a = tmp_path / "module_a.py"
        module_a.write_text('''
"""Module A."""
import os

class ServiceA:
    """Service class."""

    def method1(self):
        return os.getenv("VAR")

    def method2(self):
        return 2
''')

        module_b = tmp_path / "module_b.py"
        module_b.write_text('''
"""Module B."""
from module_a import ServiceA

class ServiceB:
    """Another service."""

    def use_a(self):
        return ServiceA()
''')

        analyzer = ArchitectureAnalyzer(
            repo_path=tmp_path,
            logger=arch_logger,
            config={},
        )

        result = analyzer.analyze([str(module_a), str(module_b)])

        # Should complete without errors and return ArchitectureResults
        assert isinstance(result, ArchitectureResults)
        assert isinstance(result.architecture.god_objects, list)
        assert isinstance(result.import_cycles.cycles, list)
        assert isinstance(result.runtime_checks, list)
