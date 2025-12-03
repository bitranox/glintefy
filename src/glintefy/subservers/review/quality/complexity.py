"""Complexity analysis module.

Analyzes code complexity using:
- Cyclomatic complexity (radon cc)
- Maintainability index (radon mi)
- Cognitive complexity (custom AST analysis)
- Function length and nesting depth
"""

import ast
import json
import subprocess
from pathlib import Path

from glintefy.config import get_timeout, get_tool_config
from glintefy.tools_venv import get_tool_path

from .analyzer_results import (
    CognitiveComplexityItem,
    ComplexityResults,
    CyclomaticComplexityItem,
    FunctionIssueItem,
    MaintainabilityItem,
)
from .base import BaseAnalyzer


class ComplexityAnalyzer(BaseAnalyzer[ComplexityResults]):
    """Analyzes code complexity metrics."""

    def analyze(self, files: list[str]) -> ComplexityResults:
        """Analyze complexity metrics for all files.

        Returns:
            ComplexityResults dataclass with complexity, maintainability, cognitive, function_issues
        """
        return ComplexityResults(
            complexity=self._analyze_cyclomatic(files),
            maintainability=self._analyze_maintainability(files),
            cognitive=self._analyze_cognitive(files),
            function_issues=self._analyze_functions(files),
        )

    def _analyze_cyclomatic(self, files: list[str]) -> list[CyclomaticComplexityItem]:
        """Analyze cyclomatic complexity using radon."""
        results: list[CyclomaticComplexityItem] = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._analyze_file_cyclomatic(file_path, radon, results)

        return results

    def _analyze_file_cyclomatic(self, file_path: str, radon: str, results: list[CyclomaticComplexityItem]) -> None:
        """Analyze cyclomatic complexity for a single file."""
        try:
            radon_cc_timeout = get_timeout("tool_quick", 60)

            # Get radon config settings
            radon_config = get_tool_config("radon")
            show_all = radon_config.get("show_all", True)
            show_average = radon_config.get("show_average", True)
            sort_by = radon_config.get("sort_by", "SCORE").upper()

            # Validate sort_by option
            valid_sort_options = ["SCORE", "LINES", "ALPHA"]
            if sort_by not in valid_sort_options:
                sort_by = "SCORE"

            # Build command with config options
            cmd = [radon, "cc", "-j", "-o", sort_by]
            if show_all:
                cmd.append("-a")  # Show all complexity ranks
            if show_average:
                cmd.append("-s")  # Show average complexity
            cmd.append(file_path)

            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=radon_cc_timeout,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return

            self._parse_radon_cc_output(result.stdout, results)

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout analyzing {file_path}")
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON from radon for {file_path}")
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")

    def _parse_radon_cc_output(self, stdout: str, results: list[CyclomaticComplexityItem]) -> None:
        """Parse radon cyclomatic complexity JSON output."""
        data = json.loads(stdout)

        for filepath, functions in data.items():
            for func in functions:
                results.append(
                    CyclomaticComplexityItem(
                        file=self._get_relative_path(filepath),
                        name=func.get("name", ""),
                        type=func.get("type", ""),
                        complexity=func.get("complexity", 0),
                        rank=func.get("rank", ""),
                        # Note: radon returns "lineno", we standardize to "line"
                        line=func.get("lineno", 0),
                    )
                )

    def _analyze_maintainability(self, files: list[str]) -> list[MaintainabilityItem]:
        """Analyze maintainability index using radon."""
        results: list[MaintainabilityItem] = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._analyze_file_maintainability(file_path, radon, results)

        return results

    def _analyze_file_maintainability(self, file_path: str, radon: str, results: list[MaintainabilityItem]) -> None:
        """Analyze maintainability index for a single file."""
        try:
            radon_mi_timeout = get_timeout("tool_quick", 60)
            result = subprocess.run(
                [radon, "mi", "-j", file_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=radon_mi_timeout,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return

            self._parse_radon_mi_output(result.stdout, results)

        except Exception as e:
            self.logger.warning(f"Error analyzing maintainability in {file_path}: {e}")

    def _parse_radon_mi_output(self, stdout: str, results: list[MaintainabilityItem]) -> None:
        """Parse radon maintainability index JSON output."""
        data = json.loads(stdout)

        for filepath, mi_data in data.items():
            results.append(
                MaintainabilityItem(
                    file=self._get_relative_path(filepath),
                    mi=mi_data.get("mi", 0),
                    rank=mi_data.get("rank", ""),
                )
            )

    def _analyze_cognitive(self, files: list[str]) -> list[CognitiveComplexityItem]:
        """Analyze cognitive complexity using custom AST analysis."""
        results: list[CognitiveComplexityItem] = []
        threshold = self.config.get("cognitive_complexity_threshold", 15)

        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._analyze_file_cognitive(file_path, threshold, results)

        return results

    def _analyze_file_cognitive(self, file_path: str, threshold: int, results: list[CognitiveComplexityItem]) -> None:
        """Analyze cognitive complexity for a single file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._record_cognitive_complexity(node, file_path, threshold, results)
        except Exception as e:
            self.logger.warning(f"Error analyzing cognitive complexity in {file_path}: {e}")

    def _record_cognitive_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, threshold: int, results: list[CognitiveComplexityItem]
    ) -> None:
        """Record cognitive complexity for a function if non-zero."""
        complexity = self._calculate_cognitive_complexity(node)

        if complexity <= 0:
            return

        results.append(
            CognitiveComplexityItem(
                file=self._get_relative_path(file_path),
                name=node.name,
                line=node.lineno,
                complexity=complexity,
                exceeds_threshold=complexity > threshold,
            )
        )

    def _calculate_cognitive_complexity(self, node: ast.AST, nesting: int = 0) -> int:
        """Calculate cognitive complexity for a node."""
        complexity = 0

        for child in ast.iter_child_nodes(node):
            complexity += self._get_child_complexity(child, nesting)

        return complexity

    def _get_child_complexity(self, child: ast.AST, nesting: int) -> int:
        """Get cognitive complexity contribution for a child node."""
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            return 1 + nesting + self._calculate_cognitive_complexity(child, nesting + 1)

        if isinstance(child, ast.ExceptHandler):
            return 1 + nesting + self._calculate_cognitive_complexity(child, nesting + 1)

        if isinstance(child, ast.BoolOp):
            return len(child.values) - 1

        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return self._calculate_cognitive_complexity(child, nesting + 1)

        return self._calculate_cognitive_complexity(child, nesting)

    def _analyze_functions(self, files: list[str]) -> list[FunctionIssueItem]:
        """Analyze function length and nesting depth."""
        results: list[FunctionIssueItem] = []
        max_length = self.config.get("max_function_length", 50)
        max_nesting = self.config.get("max_nesting_depth", 3)

        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._analyze_file_functions(file_path, max_length, max_nesting, results)

        return results

    def _analyze_file_functions(self, file_path: str, max_length: int, max_nesting: int, results: list[FunctionIssueItem]) -> None:
        """Analyze functions in a single file for length and nesting."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._check_function_issues(node, file_path, max_length, max_nesting, results)
        except Exception as e:
            self.logger.warning(f"Error analyzing functions in {file_path}: {e}")

    def _check_function_issues(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, max_length: int, max_nesting: int, results: list[FunctionIssueItem]
    ) -> None:
        """Check a function for length and nesting issues."""
        self._check_function_length(node, file_path, max_length, results)
        self._check_function_nesting(node, file_path, max_nesting, results)

    def _check_function_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, max_length: int, results: list[FunctionIssueItem]) -> None:
        """Check if function exceeds maximum length."""
        if not hasattr(node, "end_lineno"):
            return

        length = node.end_lineno - node.lineno
        if length <= max_length:
            return

        results.append(
            FunctionIssueItem(
                file=self._get_relative_path(file_path),
                function=node.name,
                line=node.lineno,
                issue_type="TOO_LONG",
                value=length,
                threshold=max_length,
                message=f"Function '{node.name}' is {length} lines (max: {max_length})",
            )
        )

    def _check_function_nesting(self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str, max_nesting: int, results: list[FunctionIssueItem]) -> None:
        """Check if function exceeds maximum nesting depth."""
        depth = self._calculate_nesting_depth(node)
        if depth <= max_nesting:
            return

        results.append(
            FunctionIssueItem(
                file=self._get_relative_path(file_path),
                function=node.name,
                line=node.lineno,
                issue_type="TOO_NESTED",
                value=depth,
                threshold=max_nesting,
                message=f"Function '{node.name}' has nesting depth {depth} (max: {max_nesting})",
            )
        )

    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in a node."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)):
                depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, depth)
            else:
                depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, depth)

        return max_depth
