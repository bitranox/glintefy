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
from typing import Any

from btx_fix_mcp.tools_venv import get_tool_path

from .base import BaseAnalyzer


class ComplexityAnalyzer(BaseAnalyzer):
    """Analyzes code complexity metrics."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Analyze complexity metrics for all files.

        Returns:
            Dictionary with keys: complexity, maintainability, cognitive, function_issues
        """
        return {
            "complexity": self._analyze_cyclomatic(files),
            "maintainability": self._analyze_maintainability(files),
            "cognitive": self._analyze_cognitive(files),
            "function_issues": self._analyze_functions(files),
        }

    def _analyze_cyclomatic(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze cyclomatic complexity using radon."""
        results = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                result = subprocess.run(
                    [radon, "cc", "-j", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, functions in data.items():
                        for func in functions:
                            results.append({
                                "file": self._get_relative_path(filepath),
                                "name": func.get("name", ""),
                                "type": func.get("type", ""),
                                "complexity": func.get("complexity", 0),
                                "rank": func.get("rank", ""),
                                "line": func.get("lineno", 0),
                            })
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout analyzing {file_path}")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from radon for {file_path}")
            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        return results

    def _analyze_maintainability(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze maintainability index using radon."""
        results = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                result = subprocess.run(
                    [radon, "mi", "-j", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, mi_data in data.items():
                        results.append({
                            "file": self._get_relative_path(filepath),
                            "mi": mi_data.get("mi", 0),
                            "rank": mi_data.get("rank", ""),
                        })
            except Exception as e:
                self.logger.warning(f"Error analyzing maintainability in {file_path}: {e}")

        return results

    def _analyze_cognitive(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze cognitive complexity using custom AST analysis."""
        results = []
        threshold = self.config.get("cognitive_complexity_threshold", 15)

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_cognitive_complexity(node)
                        if complexity > 0:
                            results.append({
                                "file": self._get_relative_path(file_path),
                                "name": node.name,
                                "line": node.lineno,
                                "complexity": complexity,
                                "exceeds_threshold": complexity > threshold,
                            })
            except Exception as e:
                self.logger.warning(f"Error analyzing cognitive complexity in {file_path}: {e}")

        return results

    def _calculate_cognitive_complexity(self, node: ast.AST, nesting: int = 0) -> int:
        """Calculate cognitive complexity for a node."""
        complexity = 0

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1 + nesting
                complexity += self._calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1 + nesting
                complexity += self._calculate_cognitive_complexity(child, nesting + 1)
            elif isinstance(child, (ast.BoolOp,)):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                complexity += self._calculate_cognitive_complexity(child, nesting + 1)
            else:
                complexity += self._calculate_cognitive_complexity(child, nesting)

        return complexity

    def _analyze_functions(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze function length and nesting depth."""
        results = []
        max_length = self.config.get("max_function_length", 50)
        max_nesting = self.config.get("max_nesting_depth", 3)

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Check function length
                        if hasattr(node, 'end_lineno'):
                            length = node.end_lineno - node.lineno
                            if length > max_length:
                                results.append({
                                    "file": self._get_relative_path(file_path),
                                    "function": node.name,
                                    "line": node.lineno,
                                    "issue_type": "TOO_LONG",
                                    "value": length,
                                    "threshold": max_length,
                                    "message": f"Function '{node.name}' is {length} lines (max: {max_length})",
                                })

                        # Check nesting depth
                        depth = self._calculate_nesting_depth(node)
                        if depth > max_nesting:
                            results.append({
                                "file": self._get_relative_path(file_path),
                                "function": node.name,
                                "line": node.lineno,
                                "issue_type": "TOO_NESTED",
                                "value": depth,
                                "threshold": max_nesting,
                                "message": f"Function '{node.name}' has nesting depth {depth} (max: {max_nesting})",
                            })
            except Exception as e:
                self.logger.warning(f"Error analyzing functions in {file_path}: {e}")

        return results

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
