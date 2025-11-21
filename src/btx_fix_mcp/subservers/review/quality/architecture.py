"""Architecture analysis module.

Analyzes code architecture for:
- God objects (classes with too many methods/lines)
- Module coupling (excessive imports)
- Import cycle detection
- Runtime check optimization opportunities
"""

import ast
from collections import defaultdict
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer


class ArchitectureAnalyzer(BaseAnalyzer):
    """Architecture analysis: god objects, coupling, import cycles."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Analyze architecture metrics.

        Returns:
            Dictionary with keys: architecture, import_cycles, runtime_checks
        """
        return {
            "architecture": self._analyze_architecture(files),
            "import_cycles": self._detect_import_cycles(files),
            "runtime_checks": self._detect_runtime_checks(files),
        }

    def _analyze_architecture(self, files: list[str]) -> dict[str, Any]:
        """Analyze architecture: god objects and module coupling."""
        god_object_methods = self.config.get("god_object_methods_threshold", 20)
        god_object_lines = self.config.get("god_object_lines_threshold", 500)
        coupling_threshold = self.config.get("coupling_threshold", 15)

        results = {
            "god_objects": [],
            "highly_coupled": [],
            "module_structure": defaultdict(list),
        }
        import_graph = defaultdict(set)

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                rel_path = self._get_relative_path(file_path)
                parts = Path(rel_path).parts
                module = parts[0] if len(parts) > 1 else "root"
                results["module_structure"][module].append(rel_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [
                            item for item in node.body
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        if hasattr(node, "end_lineno"):
                            lines = node.end_lineno - node.lineno
                            if len(methods) > god_object_methods or lines > god_object_lines:
                                results["god_objects"].append({
                                    "file": rel_path,
                                    "class": node.name,
                                    "line": node.lineno,
                                    "methods": len(methods),
                                    "lines": lines,
                                    "methods_threshold": god_object_methods,
                                    "lines_threshold": god_object_lines,
                                })
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_graph[rel_path].add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        import_graph[rel_path].add(node.module.split(".")[0])
            except Exception as e:
                self.logger.warning(f"Error analyzing architecture in {file_path}: {e}")

        for filepath, imports in import_graph.items():
            if len(imports) > coupling_threshold:
                results["highly_coupled"].append({
                    "file": filepath,
                    "import_count": len(imports),
                    "threshold": coupling_threshold,
                })

        return results

    def _detect_import_cycles(self, files: list[str]) -> dict[str, Any]:
        """Detect import cycles."""
        results = {"cycles": [], "import_graph": {}}
        import_graph: dict[str, set[str]] = defaultdict(set)

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                rel_path = self._get_relative_path(file_path)
                module_name = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py")

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_graph[module_name].add(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        import_graph[module_name].add(node.module)
            except Exception as e:
                self.logger.warning(f"Error building import graph for {file_path}: {e}")

        results["import_graph"] = {k: list(v) for k, v in import_graph.items()}

        # Simple cycle detection using DFS
        def find_cycle(
            start: str, current: str, visited: set, path: list
        ) -> list | None:
            if current in path:
                cycle_start = path.index(current)
                return path[cycle_start:] + [current]
            if current in visited:
                return None
            visited.add(current)
            path.append(current)
            for neighbor in import_graph.get(current, []):
                if neighbor in import_graph:
                    cycle = find_cycle(start, neighbor, visited, path)
                    if cycle:
                        return cycle
            path.pop()
            return None

        for module in import_graph:
            cycle = find_cycle(module, module, set(), [])
            if cycle and cycle not in results["cycles"]:
                results["cycles"].append(cycle)

        return results

    def _detect_runtime_checks(self, files: list[str]) -> list[dict[str, Any]]:
        """Detect runtime checks that could be module-level constants."""
        results = []
        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                rel_path = self._get_relative_path(file_path)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        runtime_checks = [
                            child for child in ast.walk(node)
                            if self._is_runtime_check(child)
                        ]
                        if runtime_checks:
                            results.append({
                                "file": rel_path,
                                "function": node.name,
                                "line": node.lineno,
                                "check_count": len(runtime_checks),
                                "message": (
                                    f"Function '{node.name}' has {len(runtime_checks)} "
                                    "runtime checks that could be module-level constants"
                                ),
                            })
            except Exception as e:
                self.logger.warning(f"Error detecting runtime checks in {file_path}: {e}")
        return results

    def _is_runtime_check(self, node: ast.AST) -> bool:
        """Check if a node is a runtime check that could be cached."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if hasattr(node.func.value, "id"):
                    if node.func.value.id == "os" and node.func.attr in ["getenv", "environ"]:
                        return True
                    if node.func.value.id == "sys" and node.func.attr == "platform":
                        return True
            if isinstance(node.func, ast.Name) and node.func.id in [
                "hasattr", "isinstance", "callable", "issubclass"
            ]:
                return True
        return False
