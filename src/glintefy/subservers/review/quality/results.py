"""Results compilation for quality analysis."""

from pathlib import Path

from glintefy.subservers.common.issues import QualityMetrics

from .analyzer_results import (
    CognitiveComplexityItem,
    CyclomaticComplexityItem,
    FunctionIssueItem,
    MaintainabilityItem,
    QualityAnalysisResults,
)
from .config import QualityConfig
from .issues import Issue, compile_all_issues


class ResultsCompiler:
    """Compiles and normalizes results from quality analyzers."""

    def __init__(self, quality_config: QualityConfig, repo_path: Path):
        """Initialize results compiler.

        Args:
            quality_config: Quality analysis configuration
            repo_path: Repository root path
        """
        self.quality_config = quality_config
        self.repo_path = repo_path

    def compile_issues(self, results: QualityAnalysisResults, config: QualityConfig) -> list[Issue]:
        """Compile issues from analyzer results.

        Args:
            results: Typed analyzer results
            config: Quality configuration

        Returns:
            List of Issue dataclass instances
        """
        return compile_all_issues(results, config, self.repo_path)

    def compile_metrics(
        self,
        python_files: list[str],
        js_files: list[str],
        results: QualityAnalysisResults,
        all_issues: list[Issue],
    ) -> QualityMetrics:
        """Compile all metrics from analysis results.

        Builds QualityMetrics directly from typed analyzer results without
        intermediate dict conversions.

        Args:
            python_files: List of Python files analyzed
            js_files: List of JS/TS files analyzed
            results: Typed analyzer results
            all_issues: List of Issue dataclass instances

        Returns:
            Quality metrics dataclass
        """
        thresholds = self.quality_config.thresholds
        critical_count = self._count_critical_issues(all_issues)
        total_count = len(all_issues)

        return QualityMetrics(
            # File metrics
            files_analyzed=len(python_files) + len(js_files),
            python_files=len(python_files),
            js_files=len(js_files),
            # Complexity metrics
            total_functions=len(results.complexity),
            high_complexity_count=self._count_high_complexity(results.complexity, thresholds.complexity),
            high_cognitive_count=self._count_high_cognitive(results.cognitive),
            low_mi_count=self._count_low_maintainability(results.maintainability, thresholds.maintainability),
            functions_too_long=self._count_function_issues_by_type(results.function_issues, "TOO_LONG"),
            functions_too_nested=self._count_function_issues_by_type(results.function_issues, "TOO_NESTED"),
            duplicate_blocks=len(results.duplication.duplicates),
            # Architecture metrics
            god_objects=len(results.architecture.god_objects),
            highly_coupled_modules=len(results.architecture.highly_coupled),
            # Coverage metrics
            import_cycles=len(results.import_cycles.cycles),
            dead_code_items=len(results.dead_code.dead_code),
            docstring_coverage_percent=results.docstring_coverage.coverage_percent,
            type_coverage_percent=results.type_coverage.coverage_percent,
            test_coverage_percent=0.0,
            high_churn_files=len(results.code_churn.high_churn_files),
            # Issue metrics
            beartype_passed=results.beartype.get("passed", True),
            critical_issues=critical_count,
            warning_issues=total_count - critical_count,
            total_issues=total_count,
        )

    def _count_high_complexity(self, complexity_results: list[CyclomaticComplexityItem], threshold: int) -> int:
        """Count functions exceeding complexity threshold."""
        return sum(1 for r in complexity_results if r.complexity > threshold)

    def _count_low_maintainability(self, maintainability_results: list[MaintainabilityItem], threshold: int) -> int:
        """Count files below maintainability threshold."""
        return sum(1 for r in maintainability_results if r.mi < threshold)

    def _count_function_issues_by_type(self, function_issues: list[FunctionIssueItem], issue_type: str) -> int:
        """Count function issues of specific type."""
        return sum(1 for i in function_issues if i.issue_type == issue_type)

    def _count_high_cognitive(self, cognitive_results: list[CognitiveComplexityItem]) -> int:
        """Count functions exceeding cognitive complexity threshold."""
        return sum(1 for r in cognitive_results if r.exceeds_threshold)

    def _count_critical_issues(self, all_issues: list[Issue]) -> int:
        """Count critical (error severity) issues."""
        return sum(1 for i in all_issues if i.severity == "error")
