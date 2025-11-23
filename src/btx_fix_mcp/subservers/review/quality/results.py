"""Results compilation for quality analysis."""

from pathlib import Path
from typing import Any

from btx_fix_mcp.subservers.common.issues import QualityMetrics

from .config import QualityConfig
from .issues import compile_all_issues


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

    def compile_issues(self, results: dict[str, Any], config: QualityConfig) -> list[dict[str, Any]]:
        """Compile issues from analyzer results.

        Args:
            results: Raw analyzer results
            config: Quality configuration

        Returns:
            List of normalized issues
        """
        return compile_all_issues(results, config, self.repo_path)

    def compile_metrics(
        self,
        python_files: list[str],
        js_files: list[str],
        results: dict[str, Any],
        all_issues: list[dict],
    ) -> QualityMetrics:
        """Compile all metrics from analysis results.

        Args:
            python_files: List of Python files analyzed
            js_files: List of JS/TS files analyzed
            results: Raw analyzer results
            all_issues: Compiled issues list

        Returns:
            Quality metrics dataclass
        """
        # Collect metrics from all analyzers
        file_metrics = self._compile_file_metrics(python_files, js_files)
        complexity_metrics = self._compile_complexity_metrics(results)
        architecture_metrics = self._compile_architecture_metrics(results)
        coverage_metrics = self._compile_coverage_metrics(results)
        issue_metrics = self._compile_issue_metrics(all_issues, results)

        # Build QualityMetrics dataclass
        return QualityMetrics(
            files_analyzed=file_metrics["files_analyzed"],
            python_files=file_metrics["python_files"],
            js_files=file_metrics["js_files"],
            total_functions=complexity_metrics["total_functions"],
            high_complexity_count=complexity_metrics["high_complexity_count"],
            high_cognitive_count=complexity_metrics["high_cognitive_count"],
            low_mi_count=complexity_metrics["low_mi_count"],
            functions_too_long=complexity_metrics["functions_too_long"],
            functions_too_nested=complexity_metrics["functions_too_nested"],
            god_objects=architecture_metrics["god_objects"],
            highly_coupled_modules=architecture_metrics["highly_coupled_modules"],
            import_cycles=coverage_metrics["import_cycles"],
            duplicate_blocks=complexity_metrics["duplicate_blocks"],
            dead_code_items=coverage_metrics["dead_code_items"],
            docstring_coverage_percent=coverage_metrics["docstring_coverage_percent"],
            type_coverage_percent=coverage_metrics["type_coverage_percent"],
            test_coverage_percent=0.0,  # TODO: Add test coverage computation
            high_churn_files=coverage_metrics["high_churn_files"],
            beartype_passed=issue_metrics["beartype_passed"],
            critical_issues=issue_metrics["critical_issues"],
            warning_issues=issue_metrics["issues_count"] - issue_metrics["critical_issues"],
            total_issues=issue_metrics["issues_count"],
        )

    def _compile_file_metrics(self, python_files: list[str], js_files: list[str]) -> dict[str, int]:
        """Compile file-related metrics.

        Args:
            python_files: Python files analyzed
            js_files: JS/TS files analyzed

        Returns:
            File metrics dictionary
        """
        return {
            "files_analyzed": len(python_files) + len(js_files),
            "python_files": len(python_files),
            "js_files": len(js_files),
        }

    def _compile_complexity_metrics(self, results: dict[str, Any]) -> dict[str, int]:
        """Compile complexity-related metrics.

        Args:
            results: Analyzer results

        Returns:
            Complexity metrics dictionary
        """
        thresholds = self.quality_config.thresholds
        complexity_results = results.get("complexity", [])
        maintainability_results = results.get("maintainability", [])
        cognitive_results = results.get("cognitive", [])
        function_issues = results.get("function_issues", [])

        return {
            "total_functions": len(complexity_results),
            "high_complexity_count": len([r for r in complexity_results if r.get("complexity", 0) > thresholds.complexity]),
            "low_mi_count": len([r for r in maintainability_results if r.get("mi", 100) < thresholds.maintainability]),
            "functions_too_long": len([i for i in function_issues if i["issue_type"] == "TOO_LONG"]),
            "functions_too_nested": len([i for i in function_issues if i["issue_type"] == "TOO_NESTED"]),
            "high_cognitive_count": len([r for r in cognitive_results if r.get("exceeds_threshold")]),
            "duplicate_blocks": len(results.get("duplication", {}).get("duplicates", [])),
        }

    def _compile_test_metrics(self, results: dict[str, Any]) -> dict[str, int]:
        """Compile test-related metrics.

        Args:
            results: Analyzer results

        Returns:
            Test metrics dictionary
        """
        tests = results.get("tests", {})
        return {
            "total_tests": tests.get("total_tests", 0),
            "total_assertions": tests.get("total_assertions", 0),
            "test_issues": len(tests.get("issues", [])),
        }

    def _compile_architecture_metrics(self, results: dict[str, Any]) -> dict[str, int]:
        """Compile architecture-related metrics.

        Args:
            results: Analyzer results

        Returns:
            Architecture metrics dictionary
        """
        architecture = results.get("architecture", {})
        return {
            "god_objects": len(architecture.get("god_objects", [])),
            "highly_coupled_modules": len(architecture.get("highly_coupled", [])),
            "runtime_check_optimizations": len(results.get("runtime_checks", [])),
        }

    def _compile_coverage_metrics(self, results: dict[str, Any]) -> dict[str, Any]:
        """Compile coverage-related metrics.

        Args:
            results: Analyzer results

        Returns:
            Coverage metrics dictionary
        """
        type_coverage = results.get("type_coverage", {})
        docstring_coverage = results.get("docstring_coverage", {})
        dead_code = results.get("dead_code", {})
        import_cycles = results.get("import_cycles", {})
        code_churn = results.get("code_churn", {})

        return {
            "ruff_issues": len(results.get("static", {}).get("ruff_json", [])),
            "type_coverage_percent": type_coverage.get("coverage_percent", 0),
            "docstring_coverage_percent": docstring_coverage.get("coverage_percent", 0),
            "dead_code_items": len(dead_code.get("dead_code", [])),
            "import_cycles": len(import_cycles.get("cycles", [])),
            "high_churn_files": len(code_churn.get("high_churn_files", [])),
        }

    def _compile_issue_metrics(self, all_issues: list[dict], results: dict[str, Any]) -> dict[str, Any]:
        """Compile issue-related metrics.

        Args:
            all_issues: Compiled issues list
            results: Analyzer results

        Returns:
            Issue metrics dictionary
        """
        return {
            "js_issues": len(results.get("js_analysis", {}).get("issues", [])),
            "beartype_passed": results.get("beartype", {}).get("passed", True),
            "issues_count": len(all_issues),
            "critical_issues": len([i for i in all_issues if i.get("severity") == "error"]),
        }
