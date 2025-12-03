"""Analyzer orchestration for quality sub-server."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import Logger
from pathlib import Path
from typing import Any

from .analyzer_results import (
    ArchitectureResults,
    ComplexityResults,
    MetricsResults,
    QualityAnalysisResults,
    StaticResults,
    SuiteResults,
    TypeResults,
)
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

    def _add_complexity_task(self, tasks: list, python_files: list[str]) -> None:
        """Add complexity analyzer task (always enabled)."""
        tasks.append(
            (
                "complexity",
                self.complexity_analyzer.analyze,
                python_files,
                ["complexity", "maintainability", "cognitive", "function_issues"],
            )
        )

    def _add_static_task(self, tasks: list, python_files: list[str], features) -> None:
        """Add static analyzer task if enabled."""
        if features.static_analysis or features.duplication_detection:
            tasks.append(
                (
                    "static",
                    self.static_analyzer.analyze,
                    python_files,
                    ["static", "duplication"],
                )
            )

    def _add_test_task(self, tasks: list, python_files: list[str], features) -> None:
        """Add test analyzer task if enabled."""
        if features.test_analysis:
            tasks.append(("tests", self.test_analyzer.analyze, python_files, ["tests"]))

    def _add_architecture_task(self, tasks: list, python_files: list[str], features) -> None:
        """Add architecture analyzer task if enabled."""
        if features.architecture_analysis or features.runtime_check_detection or features.import_cycle_detection:
            tasks.append(
                (
                    "architecture",
                    self.architecture_analyzer.analyze,
                    python_files,
                    ["architecture", "import_cycles", "runtime_checks"],
                )
            )

    def _add_metrics_task(self, tasks: list, all_files: list[str], features) -> None:
        """Add metrics analyzer task if enabled."""
        if features.halstead_metrics or features.raw_metrics or features.code_churn:
            tasks.append(
                (
                    "metrics",
                    self.metrics_analyzer.analyze,
                    all_files,
                    ["halstead", "raw_metrics", "code_churn"],
                )
            )

    def _add_type_task(self, tasks: list, python_files: list[str], features) -> None:
        """Add type analyzer task if enabled."""
        if features.type_coverage or features.dead_code_detection or features.docstring_coverage:
            tasks.append(
                (
                    "types",
                    self.type_analyzer.analyze,
                    python_files,
                    ["type_coverage", "dead_code", "docstring_coverage"],
                )
            )

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

        self._add_complexity_task(tasks, python_files)
        self._add_static_task(tasks, python_files, features)
        self._add_test_task(tasks, python_files, features)
        self._add_architecture_task(tasks, python_files, features)
        self._add_metrics_task(tasks, all_files, features)
        self._add_type_task(tasks, python_files, features)

        return tasks

    def execute_tasks(self, tasks: list[tuple[str, Any, list[str], list[str]]]) -> QualityAnalysisResults:
        """Execute analyzer tasks in parallel using ThreadPoolExecutor.

        Each analyzer runs in its own thread. Failures in individual analyzers
        are caught and logged, allowing other analyzers to complete.

        Args:
            tasks: List of analyzer tasks to run

        Returns:
            QualityAnalysisResults dataclass with all analyzer results
        """
        if not tasks:
            return QualityAnalysisResults()

        results = QualityAnalysisResults()

        # Run all analyzers in parallel
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(self._run_analyzer, task): task for task in tasks}
            self._collect_results(futures, results)

        return results

    def _run_analyzer(self, task: tuple[str, Any, list[str], list[str]]) -> tuple[str, Any]:
        """Run a single analyzer and return its results."""
        name, analyzer_func, files, _ = task
        try:
            return (name, analyzer_func(files))
        except Exception as e:
            self.logger.warning(f"Analyzer {name} failed: {e}")
            return (name, None)

    def _collect_results(self, futures: dict, results: QualityAnalysisResults) -> None:
        """Collect results from completed analyzer futures."""
        for future in as_completed(futures):
            task = futures[future]
            name = task[0]

            try:
                analyzer_name, analyzer_results = future.result()
                if analyzer_results is not None:
                    self._map_analyzer_results(analyzer_name, analyzer_results, results)
            except Exception as e:
                self.logger.error(f"Failed to get results from {name}: {e}")

    def _map_analyzer_results(self, analyzer_name: str, analyzer_results: Any, results: QualityAnalysisResults) -> None:
        """Map analyzer results to QualityAnalysisResults fields."""
        if isinstance(analyzer_results, ComplexityResults):
            results.complexity = analyzer_results.complexity
            results.maintainability = analyzer_results.maintainability
            results.cognitive = analyzer_results.cognitive
            results.function_issues = analyzer_results.function_issues
        elif isinstance(analyzer_results, StaticResults):
            results.static = analyzer_results.static
            results.duplication = analyzer_results.duplication
        elif isinstance(analyzer_results, SuiteResults):
            results.tests = analyzer_results
        elif isinstance(analyzer_results, ArchitectureResults):
            results.architecture = analyzer_results.architecture
            results.import_cycles = analyzer_results.import_cycles
            results.runtime_checks = analyzer_results.runtime_checks
        elif isinstance(analyzer_results, MetricsResults):
            results.halstead = analyzer_results.halstead
            results.raw_metrics = analyzer_results.raw_metrics
            results.code_churn = analyzer_results.code_churn
        elif isinstance(analyzer_results, TypeResults):
            results.type_coverage = analyzer_results.type_coverage
            results.dead_code = analyzer_results.dead_code
            results.docstring_coverage = analyzer_results.docstring_coverage

    def run_all(self, python_files: list[str], js_files: list[str]) -> QualityAnalysisResults:
        """Run all enabled analyzers (convenience method).

        Args:
            python_files: List of Python file paths
            js_files: List of JS/TS file paths

        Returns:
            QualityAnalysisResults dataclass with all analyzer results
        """
        tasks = self.build_analyzer_tasks(python_files, js_files)
        return self.execute_tasks(tasks)
