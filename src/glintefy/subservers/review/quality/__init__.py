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

from pathlib import Path

from glintefy.config import get_config, get_subserver_config
from glintefy.subservers.base import BaseSubServer, SubServerResult
from glintefy.subservers.common.issues import QualityMetrics
from glintefy.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_error_detailed,
    log_file_list,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from glintefy.subservers.common.mindsets import QUALITY_MINDSET, get_mindset
from glintefy.tools_venv import ensure_tools_venv

from .analyzer_results import QualityAnalysisResults
from .architecture import ArchitectureAnalyzer
from .complexity import ComplexityAnalyzer
from .config import QualityConfig, load_quality_config
from .files import FileManager
from .issues import Issue
from .metrics import MetricsAnalyzer
from .orchestrator import AnalyzerOrchestrator
from .results import ResultsCompiler
from .special_analyzers import BeartypeAnalyzer, JavaScriptAnalyzer
from .static import StaticAnalyzer
from .summary import generate_comprehensive_summary
from .tests import TestSuiteAnalyzer
from .types import TypeAnalyzer
from .writer import ResultsWriter

__all__ = [
    "AnalyzerOrchestrator",
    "ArchitectureAnalyzer",
    "BeartypeAnalyzer",
    "ComplexityAnalyzer",
    "FileManager",
    "JavaScriptAnalyzer",
    "MetricsAnalyzer",
    "QualityConfig",
    "QualitySubServer",
    "ResultsCompiler",
    "ResultsWriter",
    "StaticAnalyzer",
    "TestSuiteAnalyzer",
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
        output_base = base_config.get("review", {}).get("output_dir", "LLM-CONTEXT/glintefy/review")

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
            self.logger = get_mcp_logger(f"glintefy.{name}")
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

        # Initialize helper components
        self.file_manager = FileManager(self.input_dir, self.repo_path)
        self.orchestrator = AnalyzerOrchestrator(self.quality_config, self.repo_path, self.logger)
        self.orchestrator.initialize_analyzers()
        self.results_compiler = ResultsCompiler(self.quality_config, self.repo_path)
        self.results_writer = ResultsWriter(self.output_dir)
        self.js_analyzer = JavaScriptAnalyzer(self.repo_path, self.logger)
        self.beartype_analyzer = BeartypeAnalyzer(self.repo_path, self.logger)

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for quality analysis."""
        return self.file_manager.validate_inputs()

    def _load_and_validate_files(self) -> tuple[list[str], list[str]] | None:
        """Load files to analyze and return None if no files found."""
        log_step(self.logger, 1, "Loading files to analyze")
        python_files = self.file_manager.load_python_files()
        js_files = self.file_manager.load_js_files() if self.quality_config.features.js_analysis else []

        if not python_files and not js_files:
            log_result(self.logger, True, "No files to analyze")
            return None

        log_file_list(self.logger, python_files, "Python files", max_display=10)
        if js_files:
            log_file_list(self.logger, js_files, "JS/TS files", max_display=10)

        return python_files, js_files

    def _run_core_analyzers(self, python_files: list[str], js_files: list[str]) -> QualityAnalysisResults:
        """Run core analyzers in parallel."""
        log_step(self.logger, 2, "Analyzing complexity metrics")
        with LogContext(self.logger, "Complexity analysis"):
            return self.orchestrator.run_all(python_files, js_files)

    def _run_special_analyzers(self, results: QualityAnalysisResults, js_files: list[str]) -> None:
        """Run special analyzers (JS/TS, Beartype)."""
        if self.quality_config.features.js_analysis and js_files:
            log_step(self.logger, 18, "Analyzing JavaScript/TypeScript")
            with LogContext(self.logger, "JS/TS analysis"):
                results.js_analysis = self.js_analyzer.analyze(js_files)

        if self.quality_config.features.beartype:
            log_step(self.logger, 19, "Running beartype runtime type check")
            with LogContext(self.logger, "Beartype check"):
                results.beartype = self.beartype_analyzer.analyze()

    def _compile_and_save_results(
        self, results: QualityAnalysisResults, python_files: list[str], js_files: list[str]
    ) -> tuple[list[Issue], dict[str, Path], QualityMetrics, str]:
        """Compile issues, save results, and generate summary."""
        log_step(self.logger, 20, "Compiling issues")
        all_issues = self.results_compiler.compile_issues(results, self.quality_config)

        log_step(self.logger, 21, "Saving results")
        artifacts = self.results_writer.save_all_results(results, all_issues)

        metrics = self.results_compiler.compile_metrics(python_files, js_files, results, all_issues)
        summary = generate_comprehensive_summary(metrics, results, all_issues, self.mindset, self.quality_config)

        return all_issues, artifacts, metrics, summary

    def _determine_status(self, all_issues: list[Issue]) -> str:
        """Determine analysis status based on critical issues."""
        critical_issues = [i for i in all_issues if i.severity == "error"]
        return "SUCCESS" if not critical_issues else "PARTIAL"

    def execute(self) -> SubServerResult:
        """Execute comprehensive quality analysis."""
        log_section(self.logger, "QUALITY ANALYSIS")

        try:
            log_step(self.logger, 0, "Ensuring tools venv is initialized")
            ensure_tools_venv()

            files_result = self._load_and_validate_files()
            if files_result is None:
                return SubServerResult(
                    status="SUCCESS",
                    summary="# Quality Analysis\n\nNo files to analyze.",
                    artifacts={},
                    metrics={"files_analyzed": 0},
                )

            python_files, js_files = files_result
            results = self._run_core_analyzers(python_files, js_files)
            self._run_special_analyzers(results, js_files)
            all_issues, artifacts, metrics, summary = self._compile_and_save_results(results, python_files, js_files)
            status = self._determine_status(all_issues)

            log_result(self.logger, status == "SUCCESS", f"Analysis complete: {len(all_issues)} issues found")
            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=metrics.model_dump(),
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
