"""Quality sub-server: Comprehensive code quality analysis.

This sub-server analyzes code quality using multiple tools:
- Cyclomatic complexity (radon cc)
- Maintainability index (radon mi)
- Halstead metrics (radon hal)
- Raw metrics (radon raw - LOC, SLOC, comments)
- Cognitive complexity
- Function length and nesting depth
- Code duplication detection (pylint)
- Static analysis (Ruff)
- Type coverage (mypy)
- Dead code detection (vulture)
- Import cycle detection
- Docstring coverage (interrogate)
- Test suite analysis with assertion counting
- Architecture analysis (god objects, coupling)
- Runtime check optimization opportunities
- JavaScript/TypeScript analysis (eslint)
- Beartype runtime type checking
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from btx_fix_mcp.config import get_config, get_subserver_config
from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_error_detailed,
    log_file_list,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from btx_fix_mcp.subservers.common.mindsets import (
    QUALITY_MINDSET,
    get_mindset,
)
from btx_fix_mcp.tools_venv import ensure_tools_venv

from .architecture import ArchitectureAnalyzer
from .complexity import ComplexityAnalyzer
from .config import QualityConfig, get_analyzer_config, load_quality_config
from .issues import compile_all_issues
from .metrics import MetricsAnalyzer
from .summary import generate_comprehensive_summary
from .static import StaticAnalyzer
from .tests import TestAnalyzer
from .types import TypeAnalyzer

__all__ = [
    "QualitySubServer",
    "QualityConfig",
    "ArchitectureAnalyzer",
    "ComplexityAnalyzer",
    "MetricsAnalyzer",
    "StaticAnalyzer",
    "TestAnalyzer",
    "TypeAnalyzer",
]


class QualitySubServer(BaseSubServer):
    """Comprehensive code quality analyzer.

    Orchestrates multiple specialized analyzers to provide comprehensive
    quality analysis of Python and JavaScript/TypeScript codebases.
    """

    def __init__(
        self,
        name: str = "quality",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        complexity_threshold: int | None = None,
        maintainability_threshold: int | None = None,
        max_function_length: int | None = None,
        max_nesting_depth: int | None = None,
        cognitive_complexity_threshold: int | None = None,
        config_file: Path | None = None,
        mcp_mode: bool = False,
    ):
        """Initialize quality sub-server.

        Args:
            name: Sub-server name
            input_dir: Input directory (contains files_to_review.txt from scope)
            output_dir: Output directory for results
            repo_path: Repository path (default: current directory)
            complexity_threshold: Complexity threshold for warnings
            maintainability_threshold: MI threshold for warnings
            max_function_length: Max lines per function
            max_nesting_depth: Max nesting depth
            cognitive_complexity_threshold: Cognitive complexity threshold
            config_file: Path to config file
            mcp_mode: If True, log to stderr only (MCP protocol compatible).
                      If False, log to stdout only (standalone mode).
        """
        # Get output base from config for standalone use
        base_config = get_config(start_dir=str(repo_path or Path.cwd()))
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/btx_fix_mcp/review")

        if input_dir is None:
            input_dir = Path.cwd() / output_base / "scope"
        if output_dir is None:
            output_dir = Path.cwd() / output_base / name

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mcp_mode = mcp_mode

        # Initialize logger based on mode
        if mcp_mode:
            # MCP mode: stderr only (MCP protocol uses stdout)
            self.logger = get_mcp_logger(f"btx_fix_mcp.{name}")
        else:
            # Standalone mode: stdout only (no file logging)
            self.logger = setup_logger(name, log_file=None, level=20)

        # Load config using extracted config module
        raw_config = get_subserver_config("quality", start_dir=str(self.repo_path))
        self.quality_config = load_quality_config(
            raw_config,
            complexity_threshold=complexity_threshold,
            maintainability_threshold=maintainability_threshold,
            max_function_length=max_function_length,
            max_nesting_depth=max_nesting_depth,
            cognitive_complexity_threshold=cognitive_complexity_threshold,
        )

        # Expose config for external access
        self.config = raw_config

        # Load reviewer mindset for evaluation
        self.mindset = get_mindset(QUALITY_MINDSET, raw_config)

        # Initialize analyzers
        self._init_analyzers()

    def _init_analyzers(self) -> None:
        """Initialize all analyzer instances."""
        analyzer_config = get_analyzer_config(self.quality_config)

        self.complexity_analyzer = ComplexityAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.static_analyzer = StaticAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.type_analyzer = TypeAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.architecture_analyzer = ArchitectureAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.test_analyzer = TestAnalyzer(self.repo_path, self.logger, analyzer_config)
        self.metrics_analyzer = MetricsAnalyzer(self.repo_path, self.logger, analyzer_config)

    # --- Config accessor properties (for backward compatibility) ---

    @property
    def complexity_threshold(self) -> int:
        return self.quality_config.thresholds.complexity

    @property
    def maintainability_threshold(self) -> int:
        return self.quality_config.thresholds.maintainability

    @property
    def max_function_length(self) -> int:
        return self.quality_config.thresholds.max_function_length

    @property
    def max_nesting_depth(self) -> int:
        return self.quality_config.thresholds.max_nesting_depth

    @property
    def cognitive_complexity_threshold(self) -> int:
        return self.quality_config.thresholds.cognitive_complexity

    @property
    def min_type_coverage(self) -> int:
        return self.quality_config.thresholds.min_type_coverage

    @property
    def dead_code_confidence(self) -> int:
        return self.quality_config.thresholds.dead_code_confidence

    @property
    def min_docstring_coverage(self) -> int:
        return self.quality_config.thresholds.min_docstring_coverage

    @property
    def churn_threshold(self) -> int:
        return self.quality_config.thresholds.churn_threshold

    @property
    def coupling_threshold(self) -> int:
        return self.quality_config.thresholds.coupling_threshold

    @property
    def god_object_methods_threshold(self) -> int:
        return self.quality_config.thresholds.god_object_methods

    @property
    def god_object_lines_threshold(self) -> int:
        return self.quality_config.thresholds.god_object_lines

    @property
    def enable_type_coverage(self) -> bool:
        return self.quality_config.features.type_coverage

    @property
    def enable_dead_code_detection(self) -> bool:
        return self.quality_config.features.dead_code_detection

    @property
    def enable_import_cycle_detection(self) -> bool:
        return self.quality_config.features.import_cycle_detection

    @property
    def enable_docstring_coverage(self) -> bool:
        return self.quality_config.features.docstring_coverage

    @property
    def enable_halstead_metrics(self) -> bool:
        return self.quality_config.features.halstead_metrics

    @property
    def enable_raw_metrics(self) -> bool:
        return self.quality_config.features.raw_metrics

    @property
    def enable_cognitive_complexity(self) -> bool:
        return self.quality_config.features.cognitive_complexity

    @property
    def enable_js_analysis(self) -> bool:
        return self.quality_config.features.js_analysis

    @property
    def count_test_assertions(self) -> bool:
        return self.quality_config.features.test_assertions

    @property
    def enable_code_churn(self) -> bool:
        return self.quality_config.features.code_churn

    @property
    def enable_beartype(self) -> bool:
        return self.quality_config.features.beartype

    @property
    def enable_duplication_detection(self) -> bool:
        return self.quality_config.features.duplication_detection

    @property
    def enable_static_analysis(self) -> bool:
        return self.quality_config.features.static_analysis

    @property
    def enable_test_analysis(self) -> bool:
        return self.quality_config.features.test_analysis

    @property
    def enable_architecture_analysis(self) -> bool:
        return self.quality_config.features.architecture_analysis

    @property
    def enable_runtime_check_detection(self) -> bool:
        return self.quality_config.features.runtime_check_detection

    def _run_analyzers_parallel(self, python_files: list[str], js_files: list[str]) -> dict[str, Any]:
        """Run all enabled analyzers in parallel using ThreadPoolExecutor.

        Each analyzer runs in its own thread. Failures in individual analyzers
        are caught and logged, allowing other analyzers to complete.

        Args:
            python_files: List of Python file paths to analyze
            js_files: List of JS/TS file paths to analyze

        Returns:
            Dictionary with results from all analyzers
        """
        results: dict[str, Any] = {}
        all_files = python_files + js_files

        # Define analyzer tasks - each is a tuple of (name, analyzer_func, files, result_keys)
        tasks: list[tuple[str, Any, list[str], list[str]]] = []

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
        if self.enable_static_analysis or self.enable_duplication_detection:
            tasks.append(
                (
                    "static",
                    self.static_analyzer.analyze,
                    python_files,
                    ["static", "duplication"],
                )
            )

        # Test analyzer
        if self.enable_test_analysis:
            tasks.append(
                (
                    "tests",
                    self.test_analyzer.analyze,
                    python_files,
                    ["tests"],
                )
            )

        # Architecture analyzer
        if self.enable_architecture_analysis or self.enable_runtime_check_detection or self.enable_import_cycle_detection:
            tasks.append(
                (
                    "architecture",
                    self.architecture_analyzer.analyze,
                    python_files,
                    ["architecture", "import_cycles", "runtime_checks"],
                )
            )

        # Metrics analyzer
        if self.enable_halstead_metrics or self.enable_raw_metrics or self.enable_code_churn:
            tasks.append(
                (
                    "metrics",
                    self.metrics_analyzer.analyze,
                    all_files,
                    ["halstead", "raw_metrics", "code_churn"],
                )
            )

        # Type analyzer
        if self.enable_type_coverage or self.enable_dead_code_detection or self.enable_docstring_coverage:
            tasks.append(
                (
                    "types",
                    self.type_analyzer.analyze,
                    python_files,
                    ["type_coverage", "dead_code", "docstring_coverage"],
                )
            )

        def run_analyzer(task: tuple[str, Any, list[str], list[str]]) -> tuple[str, dict[str, Any]]:
            """Run a single analyzer and return its results."""
            name, analyzer_func, files, _ = task
            try:
                return (name, analyzer_func(files))
            except Exception as e:
                self.logger.warning(f"Analyzer {name} failed: {e}")
                return (name, {})

        # Run all analyzers in parallel
        with ThreadPoolExecutor(max_workers=len(tasks) if tasks else 1) as executor:
            futures = {executor.submit(run_analyzer, task): task for task in tasks}

            for future in as_completed(futures):
                task = futures[future]
                name, result_keys = task[0], task[3]
                try:
                    analyzer_name, analyzer_results = future.result()
                    # Map results to expected keys
                    for key in result_keys:
                        if key in analyzer_results:
                            results[key] = analyzer_results[key]
                        elif key == "tests" and analyzer_results:
                            # Test analyzer returns dict directly
                            results[key] = analyzer_results
                except Exception as e:
                    self.logger.error(f"Failed to get results from {name}: {e}")

        return results

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for quality analysis."""
        missing = []
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(f"No files list found in {self.input_dir}. Run scope sub-server first.")
        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute comprehensive quality analysis."""
        log_section(self.logger, "QUALITY ANALYSIS")

        try:
            # Ensure tools venv is initialized (idempotent, fast if already done)
            log_step(self.logger, 0, "Ensuring tools venv is initialized")
            ensure_tools_venv()

            # Step 1: Get files to analyze
            log_step(self.logger, 1, "Loading files to analyze")
            python_files = self._get_python_files()
            js_files = self._get_js_files() if self.enable_js_analysis else []

            if not python_files and not js_files:
                log_result(self.logger, True, "No files to analyze")
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Quality Analysis\n\nNo files to analyze.",
                    artifacts={},
                    metrics={"files_analyzed": 0},
                )

            log_file_list(self.logger, python_files, "Python files", max_display=10)
            if js_files:
                log_file_list(self.logger, js_files, "JS/TS files", max_display=10)

            # Initialize results containers
            results = {}

            # Step 2-4: Complexity analysis (cyclomatic, maintainability, cognitive, functions)
            log_step(self.logger, 2, "Analyzing complexity metrics")
            with LogContext(self.logger, "Complexity analysis"):
                complexity_results = self.complexity_analyzer.analyze(python_files)
                results["complexity"] = complexity_results.get("complexity", [])
                results["maintainability"] = complexity_results.get("maintainability", [])
                results["cognitive"] = complexity_results.get("cognitive", [])
                results["function_issues"] = complexity_results.get("function_issues", [])

            # Step 5-6: Static analysis (Ruff, duplication)
            if self.enable_static_analysis or self.enable_duplication_detection:
                log_step(self.logger, 5, "Running static analysis")
                with LogContext(self.logger, "Static analysis"):
                    static_results = self.static_analyzer.analyze(python_files)
                    if self.enable_static_analysis:
                        results["static"] = static_results.get("static", {})
                    if self.enable_duplication_detection:
                        results["duplication"] = static_results.get("duplication", {})

            # Step 7: Test suite analysis
            if self.enable_test_analysis:
                log_step(self.logger, 7, "Analyzing test suite")
                with LogContext(self.logger, "Test analysis"):
                    results["tests"] = self.test_analyzer.analyze(python_files)

            # Step 8-9: Architecture analysis
            if self.enable_architecture_analysis or self.enable_runtime_check_detection:
                log_step(self.logger, 8, "Analyzing architecture")
                with LogContext(self.logger, "Architecture analysis"):
                    arch_results = self.architecture_analyzer.analyze(python_files)
                    if self.enable_architecture_analysis:
                        results["architecture"] = arch_results.get("architecture", {})
                    if self.enable_import_cycle_detection:
                        results["import_cycles"] = arch_results.get("import_cycles", {})
                    if self.enable_runtime_check_detection:
                        results["runtime_checks"] = arch_results.get("runtime_checks", [])

            # Step 10-12: Metrics analysis (Halstead, raw, churn)
            if self.enable_halstead_metrics or self.enable_raw_metrics or self.enable_code_churn:
                log_step(self.logger, 10, "Analyzing code metrics")
                with LogContext(self.logger, "Metrics analysis"):
                    all_files = python_files + js_files
                    metrics_results = self.metrics_analyzer.analyze(all_files)
                    if self.enable_halstead_metrics:
                        results["halstead"] = metrics_results.get("halstead", [])
                    if self.enable_raw_metrics:
                        results["raw_metrics"] = metrics_results.get("raw_metrics", [])
                    if self.enable_code_churn:
                        results["code_churn"] = metrics_results.get("code_churn", {})

            # Step 13-16: Type analysis
            if self.enable_type_coverage or self.enable_dead_code_detection or self.enable_docstring_coverage:
                log_step(self.logger, 13, "Analyzing type coverage")
                with LogContext(self.logger, "Type analysis"):
                    type_results = self.type_analyzer.analyze(python_files)
                    if self.enable_type_coverage:
                        results["type_coverage"] = type_results.get("type_coverage", {})
                    if self.enable_dead_code_detection:
                        results["dead_code"] = type_results.get("dead_code", {})
                    if self.enable_docstring_coverage:
                        results["docstring_coverage"] = type_results.get("docstring_coverage", {})

            # Step 18: JavaScript/TypeScript analysis
            if self.enable_js_analysis and js_files:
                log_step(self.logger, 18, "Analyzing JavaScript/TypeScript")
                with LogContext(self.logger, "JS/TS analysis"):
                    results["js_analysis"] = self._analyze_js_files(js_files)

            # Step 19: Beartype runtime check
            if self.enable_beartype:
                log_step(self.logger, 19, "Running beartype runtime type check")
                with LogContext(self.logger, "Beartype check"):
                    results["beartype"] = self._run_beartype_check()

            # Step 20: Compile all issues
            log_step(self.logger, 20, "Compiling issues")
            all_issues = self._compile_all_issues(results)

            # Step 21: Save results
            log_step(self.logger, 21, "Saving results")
            artifacts = self._save_all_results(results, all_issues)

            # Step 22: Generate summary
            summary = self._generate_comprehensive_summary(python_files, js_files, results, all_issues)

            # Determine status
            critical_issues = [i for i in all_issues if i.get("severity") == "error"]
            status = "SUCCESS" if not critical_issues else "PARTIAL"
            log_result(self.logger, status == "SUCCESS", f"Analysis complete: {len(all_issues)} issues found")

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=self._compile_metrics(python_files, js_files, results, all_issues),
            )

        except Exception as e:
            log_error_detailed(
                self.logger,
                e,
                context={"repo_path": str(self.repo_path)},
                include_traceback=True,
            )
            return SubServerResult(
                status="FAILED",
                summary=f"# Quality Analysis Failed\n\n**Error**: {e}",
                artifacts={},
                errors=[str(e)],
            )

    def _get_python_files(self) -> list[str]:
        """Get Python files to analyze."""
        files_list = self.input_dir / "files_code.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []
        all_files = files_list.read_text().strip().split("\n")
        python_files = [f for f in all_files if f.endswith(".py") and f]
        return [str(self.repo_path / f) for f in python_files]

    def _get_js_files(self) -> list[str]:
        """Get JavaScript/TypeScript files to analyze."""
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []
        all_files = files_list.read_text().strip().split("\n")
        js_extensions = (".js", ".jsx", ".ts", ".tsx")
        js_files = [f for f in all_files if f.endswith(js_extensions) and f]
        return [str(self.repo_path / f) for f in js_files]

    def _analyze_js_files(self, files: list[str]) -> dict[str, Any]:
        """Analyze JavaScript/TypeScript files using eslint."""
        results = {"issues": [], "raw_output": ""}
        if not files:
            return results
        try:
            result = subprocess.run(
                ["eslint", "--format=json"] + files,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results["raw_output"] = result.stdout
            if result.stdout.strip():
                try:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        for message in file_result.get("messages", []):
                            results["issues"].append(
                                {
                                    "file": file_result.get("filePath", ""),
                                    "line": message.get("line", 0),
                                    "severity": "error" if message.get("severity") == 2 else "warning",
                                    "message": message.get("message", ""),
                                    "rule": message.get("ruleId", ""),
                                }
                            )
                except json.JSONDecodeError:
                    pass
        except FileNotFoundError:
            self.logger.warning("eslint not found")
        except Exception as e:
            self.logger.warning(f"eslint error: {e}")
        return results

    def _run_beartype_check(self) -> dict[str, Any]:
        """Run pytest with beartype to check runtime types."""
        results = {"passed": True, "errors": [], "raw_output": "", "skipped": False}

        # Check if tests directory exists
        tests_dir = self.repo_path / "tests"
        if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
            self.logger.info("No tests directory found, skipping beartype check")
            results["skipped"] = True
            results["raw_output"] = "Skipped: no tests directory found"
            return results

        try:
            # Check if beartype is available
            beartype_check = subprocess.run(
                ["python", "-c", "import beartype; print('available')"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if beartype_check.returncode != 0:
                self.logger.info("Beartype not installed, skipping runtime type check")
                results["skipped"] = True
                results["raw_output"] = "Skipped: beartype not installed"
                return results

            results["raw_output"] = "Beartype available\n"

            # Run actual test suite
            test_result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-x", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.repo_path),
            )
            results["raw_output"] += test_result.stdout + test_result.stderr
            if test_result.returncode != 0 and "failed" in test_result.stdout.lower():
                results["passed"] = False
                for line in test_result.stdout.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        results["errors"].append(line.strip())
        except FileNotFoundError:
            self.logger.warning("pytest not found for beartype check")
            results["skipped"] = True
        except subprocess.TimeoutExpired:
            self.logger.warning("beartype check timed out")
            results["passed"] = False
            results["errors"].append("Test run timed out")
        except Exception as e:
            self.logger.warning(f"beartype check error: {e}")
        return results

    def _compile_all_issues(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        """Compile all issues from various analyses."""
        return compile_all_issues(results, self.quality_config, self.repo_path)

    def _save_all_results(self, results: dict[str, Any], all_issues: list[dict]) -> dict[str, Path]:
        """Save all analysis results to files."""
        artifacts = {}

        # Save each result type
        for key in ["complexity", "maintainability", "function_issues", "halstead", "raw_metrics", "cognitive"]:
            if key in results and results[key]:
                path = self.output_dir / f"{key}.json"
                path.write_text(json.dumps(results[key], indent=2))
                artifacts[key] = path

        # Duplication
        if results.get("duplication", {}).get("raw_output"):
            path = self.output_dir / "duplication_analysis.txt"
            path.write_text(results["duplication"]["raw_output"])
            artifacts["duplication"] = path

        # Ruff
        if results.get("static", {}).get("ruff_json"):
            path = self.output_dir / "ruff_report.json"
            path.write_text(json.dumps(results["static"]["ruff_json"], indent=2))
            artifacts["ruff"] = path

        # Test analysis
        if results.get("tests"):
            path = self.output_dir / "test_analysis.json"
            path.write_text(json.dumps(results["tests"], indent=2))
            artifacts["test_analysis"] = path

        # Architecture
        if results.get("architecture"):
            path = self.output_dir / "architecture_analysis.json"
            arch_data = {
                "god_objects": results["architecture"].get("god_objects", []),
                "highly_coupled": results["architecture"].get("highly_coupled", []),
                "module_structure": dict(results["architecture"].get("module_structure", {})),
            }
            path.write_text(json.dumps(arch_data, indent=2))
            artifacts["architecture"] = path

        # Type coverage
        if results.get("type_coverage"):
            path = self.output_dir / "type_coverage.json"
            path.write_text(json.dumps(results["type_coverage"], indent=2))
            artifacts["type_coverage"] = path

        # Dead code
        if results.get("dead_code"):
            path = self.output_dir / "dead_code.json"
            path.write_text(json.dumps(results["dead_code"], indent=2))
            artifacts["dead_code"] = path

        # Import cycles
        if results.get("import_cycles"):
            path = self.output_dir / "import_cycles.json"
            path.write_text(json.dumps(results["import_cycles"], indent=2))
            artifacts["import_cycles"] = path

        # Docstring coverage
        if results.get("docstring_coverage"):
            path = self.output_dir / "docstring_coverage.json"
            path.write_text(json.dumps(results["docstring_coverage"], indent=2))
            artifacts["docstring_coverage"] = path

        # Code churn
        if results.get("code_churn"):
            path = self.output_dir / "code_churn.json"
            path.write_text(json.dumps(results["code_churn"], indent=2))
            artifacts["code_churn"] = path

        # JS analysis
        if results.get("js_analysis", {}).get("issues"):
            path = self.output_dir / "eslint_report.json"
            path.write_text(json.dumps(results["js_analysis"], indent=2))
            artifacts["eslint"] = path

        # Beartype
        if results.get("beartype"):
            path = self.output_dir / "beartype_check.json"
            path.write_text(json.dumps(results["beartype"], indent=2))
            artifacts["beartype"] = path

        # All issues
        if all_issues:
            path = self.output_dir / "issues.json"
            path.write_text(json.dumps(all_issues, indent=2))
            artifacts["issues"] = path

        return artifacts

    def _compile_metrics(
        self,
        python_files: list[str],
        js_files: list[str],
        results: dict[str, Any],
        all_issues: list[dict],
    ) -> dict[str, Any]:
        """Compile metrics for the result."""
        return {
            "files_analyzed": len(python_files) + len(js_files),
            "python_files": len(python_files),
            "js_files": len(js_files),
            "total_functions": len(results.get("complexity", [])),
            "high_complexity_count": len([r for r in results.get("complexity", []) if r.get("complexity", 0) > self.complexity_threshold]),
            "low_mi_count": len([r for r in results.get("maintainability", []) if r.get("mi", 100) < self.maintainability_threshold]),
            "functions_too_long": len([i for i in results.get("function_issues", []) if i["issue_type"] == "TOO_LONG"]),
            "functions_too_nested": len([i for i in results.get("function_issues", []) if i["issue_type"] == "TOO_NESTED"]),
            "high_cognitive_count": len([r for r in results.get("cognitive", []) if r.get("exceeds_threshold")]),
            "duplicate_blocks": len(results.get("duplication", {}).get("duplicates", [])),
            "total_tests": results.get("tests", {}).get("total_tests", 0),
            "total_assertions": results.get("tests", {}).get("total_assertions", 0),
            "test_issues": len(results.get("tests", {}).get("issues", [])),
            "god_objects": len(results.get("architecture", {}).get("god_objects", [])),
            "highly_coupled_modules": len(results.get("architecture", {}).get("highly_coupled", [])),
            "runtime_check_optimizations": len(results.get("runtime_checks", [])),
            "ruff_issues": len(results.get("static", {}).get("ruff_json", [])),
            "type_coverage_percent": results.get("type_coverage", {}).get("coverage_percent", 0),
            "docstring_coverage_percent": results.get("docstring_coverage", {}).get("coverage_percent", 0),
            "dead_code_items": len(results.get("dead_code", {}).get("dead_code", [])),
            "import_cycles": len(results.get("import_cycles", {}).get("cycles", [])),
            "high_churn_files": len(results.get("code_churn", {}).get("high_churn_files", [])),
            "js_issues": len(results.get("js_analysis", {}).get("issues", [])),
            "beartype_passed": results.get("beartype", {}).get("passed", True),
            "issues_count": len(all_issues),
            "critical_issues": len([i for i in all_issues if i.get("severity") == "error"]),
        }

    def _generate_comprehensive_summary(
        self,
        python_files: list[str],
        js_files: list[str],
        results: dict[str, Any],
        all_issues: list[dict],
    ) -> str:
        """Generate comprehensive markdown summary with mindset evaluation."""
        metrics = self._compile_metrics(python_files, js_files, results, all_issues)
        return generate_comprehensive_summary(metrics, results, all_issues, self.mindset, self.quality_config)
