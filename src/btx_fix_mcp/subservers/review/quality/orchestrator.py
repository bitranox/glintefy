"""Analyzer orchestration for quality sub-server."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import Logger
from pathlib import Path
from typing import Any

from .architecture import ArchitectureAnalyzer
from .complexity import ComplexityAnalyzer
from .config import QualityConfig, get_analyzer_config
from .metrics import MetricsAnalyzer
from .static import StaticAnalyzer
from .tests import TestSuiteAnalyzer
from .types import TypeAnalyzer


class AnalyzerOrchestrator:
    """Orchestrates running multiple code quality analyzers."""

    def __init__(self, quality_config: QualityConfig, repo_path: Path, logger: Logger):
        """Initialize orchestrator.

        Args:
            quality_config: Quality analysis configuration
            repo_path: Repository root path
            logger: Logger instance
        """
        self.quality_config = quality_config
        self.repo_path = repo_path
        self.logger = logger
        self._analyzers_initialized = False

    def initialize_analyzers(self) -> None:
        """Initialize all analyzer instances."""
        if self._analyzers_initialized:
            return

        analyzer_config = get_analyzer_config(self.quality_config)

        self.complexity_analyzer = ComplexityAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.static_analyzer = StaticAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.type_analyzer = TypeAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.architecture_analyzer = ArchitectureAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.test_analyzer = TestSuiteAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.metrics_analyzer = MetricsAnalyzer(self.repo_path, self.logger, analyzer_config)

        self._analyzers_initialized = True

    def build_analyzer_tasks(self, python_files: list[str], js_files: list[str]) -> list[tuple[str, Any, list[str], list[str]]]:
        """Build list of analyzer tasks based on enabled features.

        Args:
            python_files: List of Python file paths
            js_files: List of JS/TS file paths

        Returns:
            List of tasks, each a tuple of (name, analyzer_func, files, result_keys)
        """
        if not self._analyzers_initialized:
            self.initialize_analyzers()

        tasks: list[tuple[str, Any, list[str], list[str]]] = []
        all_files = python_files + js_files
        features = self.quality_config.features

        # Complexity analyzer (always enabled)
        tasks.append(
            (
                "complexity",
                self.complexity_analyzer.analyze,
                python_files,
                ["complexity", "maintainability", "cognitive", "function_issues"],
            )
        )

        # Static analyzer
        if features.static_analysis or features.duplication_detection:
            tasks.append(
                (
                    "static",
                    self.static_analyzer.analyze,
                    python_files,
                    ["static", "duplication"],
                )
            )

        # Test analyzer
        if features.test_analysis:
            tasks.append(("tests", self.test_analyzer.analyze, python_files, ["tests"]))

        # Architecture analyzer
        if features.architecture_analysis or features.runtime_check_detection or features.import_cycle_detection:
            tasks.append(
                (
                    "architecture",
                    self.architecture_analyzer.analyze,
                    python_files,
                    ["architecture", "import_cycles", "runtime_checks"],
                )
            )

        # Metrics analyzer
        if features.halstead_metrics or features.raw_metrics or features.code_churn:
            tasks.append(
                (
                    "metrics",
                    self.metrics_analyzer.analyze,
                    all_files,
                    ["halstead", "raw_metrics", "code_churn"],
                )
            )

        # Type analyzer
        if features.type_coverage or features.dead_code_detection or features.docstring_coverage:
            tasks.append(
                (
                    "types",
                    self.type_analyzer.analyze,
                    python_files,
                    ["type_coverage", "dead_code", "docstring_coverage"],
                )
            )

        return tasks

    def execute_tasks(self, tasks: list[tuple[str, Any, list[str], list[str]]]) -> dict[str, Any]:
        """Execute analyzer tasks in parallel using ThreadPoolExecutor.

        Each analyzer runs in its own thread. Failures in individual analyzers
        are caught and logged, allowing other analyzers to complete.

        Args:
            tasks: List of analyzer tasks to run

        Returns:
            Dictionary with results from all analyzers
        """
        if not tasks:
            return {}

        results: dict[str, Any] = {}

        # Run all analyzers in parallel
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(self._run_analyzer, task): task for task in tasks}
            self._collect_results(futures, results)

        return results

    def _run_analyzer(self, task: tuple[str, Any, list[str], list[str]]) -> tuple[str, dict[str, Any]]:
        """Run a single analyzer and return its results."""
        name, analyzer_func, files, _ = task
        try:
            return (name, analyzer_func(files))
        except Exception as e:
            self.logger.warning(f"Analyzer {name} failed: {e}")
            return (name, {})

    def _collect_results(self, futures: dict, results: dict[str, Any]) -> None:
        """Collect results from completed analyzer futures."""
        for future in as_completed(futures):
            task = futures[future]
            name, result_keys = task[0], task[3]

            try:
                analyzer_name, analyzer_results = future.result()
                self._map_analyzer_results(result_keys, analyzer_results, results)
            except Exception as e:
                self.logger.error(f"Failed to get results from {name}: {e}")

    def _map_analyzer_results(self, result_keys: list[str], analyzer_results: dict[str, Any], results: dict[str, Any]) -> None:
        """Map analyzer results to expected result keys."""
        for key in result_keys:
            if key in analyzer_results:
                results[key] = analyzer_results[key]
            elif key == "tests" and analyzer_results:
                # Test analyzer returns dict directly
                results[key] = analyzer_results

    def run_all(self, python_files: list[str], js_files: list[str]) -> dict[str, Any]:
        """Run all enabled analyzers (convenience method).

        Args:
            python_files: List of Python file paths
            js_files: List of JS/TS file paths

        Returns:
            Dictionary with results from all analyzers
        """
        tasks = self.build_analyzer_tasks(python_files, js_files)
        return self.execute_tasks(tasks)
