"""Test analysis module.

Analyzes test suites for:
- Test count and assertion counting
- Test categorization (unit, integration, e2e)
- Test quality issues (no assertions, long tests)
- OS-specific test decorator detection
"""

import ast
from pathlib import Path

from .analyzer_results import SuiteFileInfo, SuiteIssueItem, SuiteResults
from .base import BaseAnalyzer


class TestSuiteAnalyzer(BaseAnalyzer[SuiteResults]):
    """Test suite analyzer with assertion counting and OS-specific detection."""

    __test__ = False  # Tell pytest this is not a test class

    def analyze(self, files: list[str]) -> SuiteResults:
        """Analyze test suite.

        Returns:
            SuiteResults dataclass with test files info, counts, categories, and issues.
        """
        results = SuiteResults()
        test_files = self._identify_test_files(files)

        for file_path in test_files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                rel_path = self._get_relative_path(file_path)
                file_info = SuiteFileInfo(file=rel_path)

                # Categorize test file
                path_lower = file_path.lower()
                if "unit" in path_lower:
                    results.categories.unit += 1
                elif "integration" in path_lower:
                    results.categories.integration += 1
                elif "e2e" in path_lower or "end_to_end" in path_lower:
                    results.categories.e2e += 1
                else:
                    results.categories.unknown += 1

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("test_"):
                            file_info.test_count += 1
                            results.total_tests += 1

                            # Count assertions
                            assertion_count = self._count_assertions(node)
                            file_info.assertion_count += assertion_count
                            results.total_assertions += assertion_count

                            if assertion_count == 0:
                                issue = SuiteIssueItem(
                                    type="NO_ASSERTIONS",
                                    file=rel_path,
                                    line=node.lineno,
                                    message=f"Test '{node.name}' has no assertions",
                                )
                                file_info.issues.append(issue)
                                results.issues.append(issue)

                            # Check test length
                            if hasattr(node, "end_lineno"):
                                length = node.end_lineno - node.lineno
                                if length > 50:
                                    issue = SuiteIssueItem(
                                        type="LONG_TEST",
                                        file=rel_path,
                                        line=node.lineno,
                                        message=f"Test '{node.name}' is {length} lines (should be <50)",
                                    )
                                    file_info.issues.append(issue)
                                    results.issues.append(issue)

                            # Check for OS-specific code without proper decorators
                            os_issue = self._check_os_specific_test(node, rel_path)
                            if os_issue:
                                file_info.issues.append(os_issue)
                                results.issues.append(os_issue)

                results.test_files.append(file_info)
            except Exception as e:
                self.logger.warning(f"Error analyzing test file {file_path}: {e}")

        return results

    def _identify_test_files(self, files: list[str]) -> list[str]:
        """Identify test files from a list of files."""
        test_files = []
        for f in files:
            path = Path(f)
            name = path.name.lower()
            # Standard pytest naming conventions
            if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
                test_files.append(f)
            # Files in tests/ directory (any level)
            elif "tests" in path.parts or "test" in path.parts:
                if name.endswith(".py"):
                    test_files.append(f)
        return test_files

    def _count_assertions(self, node: ast.FunctionDef) -> int:
        """Count assertions in a test function."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                count += 1
            elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if "assert" in child.func.attr.lower():
                    count += 1
        return count

    def _check_os_specific_test(self, node: ast.FunctionDef, file_path: str) -> SuiteIssueItem | None:
        """Check if test has OS-specific code without proper skip decorators.

        Detects:
        - sys.platform checks
        - os.name checks
        - platform.system() calls
        - Custom decorators with platform/os/skip keywords
        """
        # Keywords that indicate OS-aware decorators (standard and custom)
        os_decorator_keywords = {
            "skip",
            "skipif",
            "skipunless",
            "platform",
            "windows",
            "linux",
            "darwin",
            "macos",
            "unix",
            "posix",
            "nt",
            "os_specific",
            "requires_",
        }

        # Check if test has OS-aware decorators
        has_os_decorator = False
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator).lower()
            if any(kw in decorator_name for kw in os_decorator_keywords):
                has_os_decorator = True
                break

        # Check if test body contains OS-specific checks
        os_checks_found = []
        for child in ast.walk(node):
            # sys.platform
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == "sys" and child.attr == "platform":
                    os_checks_found.append("sys.platform")
            # os.name
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == "os" and child.attr == "name":
                    os_checks_found.append("os.name")
            # platform.system() or platform.platform()
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if isinstance(child.func.value, ast.Name) and child.func.value.id == "platform":
                    if child.func.attr in ("system", "platform", "machine", "node"):
                        os_checks_found.append(f"platform.{child.func.attr}()")
            # String comparisons with OS names in conditionals
            if isinstance(child, ast.Compare):
                for comparator in child.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                        val = comparator.value.lower()
                        if val in ("win32", "linux", "darwin", "nt", "posix", "windows", "macos"):
                            if "sys.platform" not in os_checks_found and "os.name" not in os_checks_found:
                                os_checks_found.append(f"OS comparison: '{comparator.value}'")

        # If OS checks found but no decorator, flag it
        if os_checks_found and not has_os_decorator:
            unique_checks = list(set(os_checks_found))
            return SuiteIssueItem(
                type="MISSING_OS_DECORATOR",
                file=file_path,
                line=node.lineno,
                function=node.name,
                os_checks=unique_checks,
                message=f"Test '{node.name}' uses {', '.join(unique_checks)} but lacks @pytest.mark.skipif decorator",
            )
        return None

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            # Handle chained attributes like pytest.mark.skipif
            parts = []
            node = decorator
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""
