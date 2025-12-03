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

from .analyzer_results import (
    ArchitectureMetrics,
    ArchitectureResults,
    GodObjectInfo,
    HighCouplingInfo,
    ImportCycleResults,
    RuntimeCheckInfo,
)
from .base import BaseAnalyzer


class ArchitectureAnalyzer(BaseAnalyzer[ArchitectureResults]):
    """Architecture analysis: god objects, coupling, import cycles."""

    def analyze(self, files: list[str]) -> ArchitectureResults:
        """Analyze architecture metrics.

        Returns:
            ArchitectureResults dataclass with architecture, import_cycles, runtime_checks
        """
        return ArchitectureResults(
            architecture=self._analyze_architecture(files),
            import_cycles=self._detect_import_cycles(files),
            runtime_checks=self._detect_runtime_checks(files),
        )

    def _analyze_architecture(self, files: list[str]) -> ArchitectureMetrics:
        """Analyze architecture: god objects and module coupling."""
        # Check feature flags
        detect_god_objects = self.config.get("detect_god_objects", True)
        detect_high_coupling = self.config.get("detect_high_coupling", True)

        god_object_methods = self.config.get("god_object_methods_threshold", 20)
        god_object_lines = self.config.get("god_object_lines_threshold", 500)
        coupling_threshold = self.config.get("coupling_threshold", 15)

        god_objects: list[GodObjectInfo] = []
        highly_coupled: list[HighCouplingInfo] = []
        module_structure: dict[str, list[str]] = defaultdict(list)
        import_graph: dict[str, set[str]] = defaultdict(set)

        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._analyze_single_file(
                file_path,
                god_objects,
                highly_coupled,
                module_structure,
                import_graph,
                god_object_methods,
                god_object_lines,
                detect_god_objects,
            )

        if detect_high_coupling:
            self._identify_highly_coupled(import_graph, highly_coupled, coupling_threshold)

        return ArchitectureMetrics(
            god_objects=god_objects,
            highly_coupled=highly_coupled,
            module_structure=dict(module_structure),
        )

    def _analyze_single_file(
        self,
        file_path: str,
        god_objects: list[GodObjectInfo],
        highly_coupled: list[HighCouplingInfo],
        module_structure: dict[str, list[str]],
        import_graph: dict[str, set[str]],
        god_object_methods: int,
        god_object_lines: int,
        detect_god_objects: bool,
    ) -> None:
        """Analyze a single file for god objects and imports."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            rel_path = self._get_relative_path(file_path)

            self._update_module_structure(rel_path, module_structure)

            for node in ast.walk(tree):
                self._process_node(
                    node,
                    rel_path,
                    god_objects,
                    import_graph,
                    god_object_methods,
                    god_object_lines,
                    detect_god_objects,
                )
        except Exception as e:
            self.logger.warning(f"Error analyzing architecture in {file_path}: {e}")

    def _update_module_structure(self, rel_path: str, module_structure: dict[str, list[str]]) -> None:
        """Update module structure with file path."""
        parts = Path(rel_path).parts
        module = parts[0] if len(parts) > 1 else "root"
        module_structure[module].append(rel_path)

    def _process_node(
        self,
        node: ast.AST,
        rel_path: str,
        god_objects: list[GodObjectInfo],
        import_graph: dict[str, set[str]],
        god_object_methods: int,
        god_object_lines: int,
        detect_god_objects: bool,
    ) -> None:
        """Process AST node for god objects and imports."""
        if isinstance(node, ast.ClassDef):
            if detect_god_objects:
                self._check_god_object(node, rel_path, god_objects, god_object_methods, god_object_lines)
        elif isinstance(node, ast.Import):
            self._process_import(node, rel_path, import_graph)
        elif isinstance(node, ast.ImportFrom):
            self._process_import_from(node, rel_path, import_graph)

    def _check_god_object(
        self,
        node: ast.ClassDef,
        rel_path: str,
        god_objects: list[GodObjectInfo],
        god_object_methods: int,
        god_object_lines: int,
    ) -> None:
        """Check if class is a god object."""
        methods = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]

        if not hasattr(node, "end_lineno"):
            return

        lines = node.end_lineno - node.lineno
        if len(methods) <= god_object_methods and lines <= god_object_lines:
            return

        god_objects.append(
            GodObjectInfo(
                file=rel_path,
                class_name=node.name,
                line=node.lineno,
                methods=len(methods),
                lines=lines,
                methods_threshold=god_object_methods,
                lines_threshold=god_object_lines,
            )
        )

    def _process_import(self, node: ast.Import, rel_path: str, import_graph: dict[str, set[str]]) -> None:
        """Process import statement."""
        for alias in node.names:
            import_graph[rel_path].add(alias.name.split(".")[0])

    def _process_import_from(self, node: ast.ImportFrom, rel_path: str, import_graph: dict[str, set[str]]) -> None:
        """Process from-import statement."""
        if node.module:
            import_graph[rel_path].add(node.module.split(".")[0])

    def _identify_highly_coupled(self, import_graph: dict[str, set[str]], highly_coupled: list[HighCouplingInfo], coupling_threshold: int) -> None:
        """Identify highly coupled modules."""
        for filepath, imports in import_graph.items():
            if len(imports) > coupling_threshold:
                highly_coupled.append(
                    HighCouplingInfo(
                        file=filepath,
                        import_count=len(imports),
                        threshold=coupling_threshold,
                    )
                )

    def _detect_import_cycles(self, files: list[str]) -> ImportCycleResults:
        """Detect import cycles."""
        cycles: list[list[str]] = []
        import_graph: dict[str, set[str]] = defaultdict(set)

        self._build_import_graph(files, import_graph)
        self._find_all_cycles(import_graph, cycles)

        return ImportCycleResults(
            cycles=cycles,
            import_graph={k: list(v) for k, v in import_graph.items()},
        )

    def _build_import_graph(self, files: list[str], import_graph: dict[str, set[str]]) -> None:
        """Build import graph from files."""
        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._extract_imports_from_file(file_path, import_graph)

    def _extract_imports_from_file(self, file_path: str, import_graph: dict[str, set[str]]) -> None:
        """Extract imports from a single file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            rel_path = self._get_relative_path(file_path)
            module_name = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py")

            for node in ast.walk(tree):
                self._add_import_to_graph(node, module_name, import_graph)
        except Exception as e:
            self.logger.warning(f"Error building import graph for {file_path}: {e}")

    def _add_import_to_graph(self, node: ast.AST, module_name: str, import_graph: dict[str, set[str]]) -> None:
        """Add import node to graph."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_graph[module_name].add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            import_graph[module_name].add(node.module)

    def _find_all_cycles(self, import_graph: dict[str, set[str]], cycles: list[list[str]]) -> None:
        """Find all import cycles in the graph."""
        for module in import_graph:
            cycle = self._find_cycle_from_module(module, import_graph)
            if cycle and cycle not in cycles:
                cycles.append(cycle)

    def _find_cycle_from_module(self, module: str, import_graph: dict[str, set[str]]) -> list | None:
        """Find cycle starting from given module using DFS."""
        return self._dfs_find_cycle(module, module, import_graph, set(), [])

    def _dfs_find_cycle(self, start: str, current: str, import_graph: dict[str, set[str]], visited: set, path: list) -> list | None:
        """Detect import cycles using depth-first search."""
        if current in path:
            cycle_start = path.index(current)
            return path[cycle_start:] + [current]

        if current in visited:
            return None

        visited.add(current)
        path.append(current)

        for neighbor in import_graph.get(current, []):
            if neighbor not in import_graph:
                continue

            cycle = self._dfs_find_cycle(start, neighbor, import_graph, visited, path)
            if cycle:
                return cycle

        path.pop()
        return None

    def _detect_runtime_checks(self, files: list[str]) -> list[RuntimeCheckInfo]:
        """Detect runtime checks that could be module-level constants."""
        results: list[RuntimeCheckInfo] = []
        for file_path in files:
            if not Path(file_path).exists():
                continue

            self._scan_file_for_runtime_checks(file_path, results)

        return results

    def _scan_file_for_runtime_checks(self, file_path: str, results: list[RuntimeCheckInfo]) -> None:
        """Scan a single file for runtime checks."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            rel_path = self._get_relative_path(file_path)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._check_function_for_runtime_checks(node, rel_path, results)
        except Exception as e:
            self.logger.warning(f"Error detecting runtime checks in {file_path}: {e}")

    def _check_function_for_runtime_checks(self, node: ast.FunctionDef | ast.AsyncFunctionDef, rel_path: str, results: list[RuntimeCheckInfo]) -> None:
        """Check a function for runtime checks."""
        runtime_checks = [child for child in ast.walk(node) if self._is_runtime_check(child)]

        if not runtime_checks:
            return

        results.append(
            RuntimeCheckInfo(
                file=rel_path,
                function=node.name,
                line=node.lineno,
                check_count=len(runtime_checks),
                message=f"Function '{node.name}' has {len(runtime_checks)} runtime checks that could be module-level constants",
            )
        )

    def _is_runtime_check(self, node: ast.AST) -> bool:
        """Check if a node is a runtime check that could be cached."""
        if not isinstance(node, ast.Call):
            return False

        return self._is_attribute_runtime_check(node) or self._is_builtin_runtime_check(node)

    def _is_attribute_runtime_check(self, node: ast.Call) -> bool:
        """Check if node is an attribute-based runtime check (os.getenv, sys.platform)."""
        if not isinstance(node.func, ast.Attribute):
            return False

        if not hasattr(node.func.value, "id"):
            return False

        module_id = node.func.value.id
        attr_name = node.func.attr

        if module_id == "os" and attr_name in ["getenv", "environ"]:
            return True

        if module_id == "sys" and attr_name == "platform":
            return True

        return False

    def _is_builtin_runtime_check(self, node: ast.Call) -> bool:
        """Check if node is a builtin runtime check (isinstance, hasattr, etc)."""
        if not isinstance(node.func, ast.Name):
            return False

        return node.func.id in ["hasattr", "isinstance", "callable", "issubclass"]
