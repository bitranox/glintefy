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
from pathlib import Path
from typing import Any

from btx_fix_mcp.config import get_subserver_config
from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.logging import (
    LogContext,
    log_file_list,
    log_result,
    log_section,
    log_step,
    setup_logger,
)
from btx_fix_mcp.tools_venv import ensure_tools_venv

from .architecture import ArchitectureAnalyzer
from .complexity import ComplexityAnalyzer
from .metrics import MetricsAnalyzer
from .static import StaticAnalyzer
from .tests import TestAnalyzer
from .types import TypeAnalyzer

__all__ = [
    "QualitySubServer",
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
    ):
        """Initialize quality sub-server."""
        if input_dir is None:
            input_dir = Path.cwd() / "LLM-CONTEXT" / "review-anal" / "scope"
        if output_dir is None:
            output_dir = Path.cwd() / "LLM-CONTEXT" / "review-anal" / name

        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()

        # Initialize logger
        self.logger = setup_logger(
            name, log_file=self.output_dir / f"{name}.log", level=20
        )

        # Load config from lib_layered_config
        config = get_subserver_config("quality", start_dir=str(self.repo_path))
        self.config = config

        # Core thresholds
        self.complexity_threshold = (
            complexity_threshold if complexity_threshold is not None
            else config.get("complexity_threshold", 10)
        )
        self.maintainability_threshold = (
            maintainability_threshold if maintainability_threshold is not None
            else config.get("maintainability_threshold", 20)
        )
        self.max_function_length = (
            max_function_length if max_function_length is not None
            else config.get("max_function_length", 50)
        )
        self.max_nesting_depth = (
            max_nesting_depth if max_nesting_depth is not None
            else config.get("max_nesting_depth", 3)
        )
        self.cognitive_complexity_threshold = (
            cognitive_complexity_threshold if cognitive_complexity_threshold is not None
            else config.get("cognitive_complexity_threshold", 15)
        )

        # Feature flags from config
        self.enable_type_coverage = config.get("enable_type_coverage", True)
        self.enable_dead_code_detection = config.get("enable_dead_code_detection", True)
        self.enable_import_cycle_detection = config.get("enable_import_cycle_detection", True)
        self.enable_docstring_coverage = config.get("enable_docstring_coverage", True)
        self.enable_halstead_metrics = config.get("enable_halstead_metrics", True)
        self.enable_raw_metrics = config.get("enable_raw_metrics", True)
        self.enable_cognitive_complexity = config.get("enable_cognitive_complexity", True)
        self.enable_js_analysis = config.get("enable_js_analysis", True)
        self.count_test_assertions = config.get("count_test_assertions", True)
        self.enable_code_churn = config.get("enable_code_churn", True)
        self.enable_beartype = config.get("enable_beartype", True)
        self.enable_duplication_detection = config.get(
            "enable_duplication_detection", config.get("detect_duplication", True)
        )
        self.enable_static_analysis = config.get("enable_static_analysis", True)
        self.enable_test_analysis = config.get("enable_test_analysis", True)
        self.enable_architecture_analysis = config.get("enable_architecture_analysis", True)
        self.enable_runtime_check_detection = config.get("enable_runtime_check_detection", True)

        # Additional thresholds
        self.min_type_coverage = config.get("min_type_coverage", 80)
        self.dead_code_confidence = config.get("dead_code_confidence", 80)
        self.min_docstring_coverage = config.get("min_docstring_coverage", 80)
        self.churn_threshold = config.get("churn_threshold", 20)
        self.coupling_threshold = config.get("coupling_threshold", 15)
        self.god_object_methods_threshold = config.get("god_object_methods_threshold", 20)
        self.god_object_lines_threshold = config.get("god_object_lines_threshold", 500)

        # Initialize analyzers
        self._init_analyzers()

    def _init_analyzers(self) -> None:
        """Initialize all analyzer instances."""
        analyzer_config = {
            "complexity_threshold": self.complexity_threshold,
            "maintainability_threshold": self.maintainability_threshold,
            "max_function_length": self.max_function_length,
            "max_nesting_depth": self.max_nesting_depth,
            "cognitive_complexity_threshold": self.cognitive_complexity_threshold,
            "dead_code_confidence": self.dead_code_confidence,
            "churn_threshold": self.churn_threshold,
            "coupling_threshold": self.coupling_threshold,
            "god_object_methods_threshold": self.god_object_methods_threshold,
            "god_object_lines_threshold": self.god_object_lines_threshold,
        }

        self.complexity_analyzer = ComplexityAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )
        self.static_analyzer = StaticAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )
        self.type_analyzer = TypeAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )
        self.architecture_analyzer = ArchitectureAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )
        self.test_analyzer = TestAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )
        self.metrics_analyzer = MetricsAnalyzer(
            self.repo_path, self.logger, analyzer_config
        )

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for quality analysis."""
        missing = []
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(
                    f"No files list found in {self.input_dir}. Run scope sub-server first."
                )
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
            summary = self._generate_comprehensive_summary(
                python_files, js_files, results, all_issues
            )

            # Determine status
            critical_issues = [i for i in all_issues if i.get("severity") == "error"]
            status = "SUCCESS" if not critical_issues else "PARTIAL"
            log_result(
                self.logger, status == "SUCCESS",
                f"Analysis complete: {len(all_issues)} issues found"
            )

            return SubServerResult(
                status=status,
                summary=summary,
                artifacts=artifacts,
                metrics=self._compile_metrics(python_files, js_files, results, all_issues),
            )

        except Exception as e:
            self.logger.error(f"Quality analysis failed: {e}", exc_info=True)
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
                capture_output=True, text=True, timeout=60,
            )
            results["raw_output"] = result.stdout
            if result.stdout.strip():
                try:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        for message in file_result.get("messages", []):
                            results["issues"].append({
                                "file": file_result.get("filePath", ""),
                                "line": message.get("line", 0),
                                "severity": "error" if message.get("severity") == 2 else "warning",
                                "message": message.get("message", ""),
                                "rule": message.get("ruleId", ""),
                            })
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
                capture_output=True, text=True, timeout=10,
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
                capture_output=True, text=True, timeout=120, cwd=str(self.repo_path),
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
        issues = []

        # Complexity issues
        for r in results.get("complexity", []):
            if r.get("complexity", 0) > self.complexity_threshold:
                issues.append({
                    "type": "high_complexity",
                    "severity": "warning" if r["complexity"] <= 20 else "error",
                    "file": r["file"], "line": r.get("lineno", 0), "name": r["name"],
                    "value": r["complexity"], "threshold": self.complexity_threshold,
                    "message": f"Function '{r['name']}' has complexity {r['complexity']} (threshold: {self.complexity_threshold})",
                })

        # Maintainability issues
        for r in results.get("maintainability", []):
            if r.get("mi", 100) < self.maintainability_threshold:
                issues.append({
                    "type": "low_maintainability",
                    "severity": "warning" if r["mi"] >= 10 else "error",
                    "file": r["file"], "value": r["mi"],
                    "threshold": self.maintainability_threshold,
                    "message": f"File has maintainability index {r['mi']:.1f} (threshold: {self.maintainability_threshold})",
                })

        # Function issues
        for issue in results.get("function_issues", []):
            issues.append({
                "type": issue["issue_type"].lower(),
                "severity": "error" if issue["value"] > issue["threshold"] * 2 else "warning",
                "file": issue["file"], "line": issue["line"], "name": issue["function"],
                "value": issue["value"], "threshold": issue["threshold"],
                "message": issue["message"],
            })

        # Cognitive complexity issues
        for r in results.get("cognitive", []):
            if r.get("exceeds_threshold"):
                issues.append({
                    "type": "high_cognitive_complexity", "severity": "warning",
                    "file": r["file"], "line": r["line"], "name": r["function"],
                    "value": r["cognitive_complexity"],
                    "threshold": self.cognitive_complexity_threshold,
                    "message": f"Function '{r['function']}' has cognitive complexity {r['cognitive_complexity']} (threshold: {self.cognitive_complexity_threshold})",
                })

        # Test issues
        for test_issue in results.get("tests", {}).get("issues", []):
            issue_type = test_issue.get("type", "test_issue").lower()
            issues.append({
                "type": issue_type, "severity": "warning",
                "file": test_issue.get("file", ""),
                "line": test_issue.get("line", 0),
                "message": test_issue.get("message", ""),
            })

        # Architecture issues
        arch = results.get("architecture", {})
        for obj in arch.get("god_objects", []):
            issues.append({
                "type": "god_object", "severity": "error",
                "file": obj["file"], "line": obj["line"], "name": obj["class"],
                "value": f"{obj['methods']} methods, {obj['lines']} lines",
                "message": f"Class '{obj['class']}' is a god object ({obj['methods']} methods, {obj['lines']} lines)",
            })
        for item in arch.get("highly_coupled", []):
            threshold = item.get("threshold", self.coupling_threshold)
            issues.append({
                "type": "high_coupling", "severity": "warning",
                "file": item["file"], "value": item["import_count"],
                "threshold": threshold,
                "message": f"Module has {item['import_count']} imports (threshold: {threshold})",
            })

        # Runtime check optimization issues
        for rc in results.get("runtime_checks", []):
            issues.append({
                "type": "runtime_check_optimization", "severity": "info",
                "file": rc["file"], "line": rc["line"], "name": rc["function"],
                "value": rc["check_count"], "message": rc["message"],
            })

        # Ruff static analysis issues
        for ruff_issue in results.get("static", {}).get("ruff_json", []):
            try:
                file_path = ruff_issue.get("filename", "")
                rel_path = str(Path(file_path).relative_to(self.repo_path)) if file_path else ""
            except ValueError:
                rel_path = file_path
            issues.append({
                "type": f"ruff_{ruff_issue.get('code', 'unknown')}", "severity": "warning",
                "file": rel_path,
                "line": ruff_issue.get("location", {}).get("row", 0),
                "message": ruff_issue.get("message", ""),
                "rule": ruff_issue.get("code", ""),
            })

        # Duplication issues
        for dup in results.get("duplication", {}).get("duplicates", []):
            issues.append({"type": "code_duplication", "severity": "warning", "message": dup})

        # Type coverage issues
        type_cov = results.get("type_coverage", {})
        if type_cov.get("coverage_percent", 100) < self.min_type_coverage:
            issues.append({
                "type": "low_type_coverage", "severity": "warning",
                "value": type_cov["coverage_percent"], "threshold": self.min_type_coverage,
                "message": f"Type coverage is {type_cov['coverage_percent']}% (minimum: {self.min_type_coverage}%)",
            })

        # Docstring coverage issues
        doc_cov = results.get("docstring_coverage", {})
        if doc_cov.get("coverage_percent", 100) < self.min_docstring_coverage:
            issues.append({
                "type": "low_docstring_coverage", "severity": "warning",
                "value": doc_cov["coverage_percent"], "threshold": self.min_docstring_coverage,
                "message": f"Docstring coverage is {doc_cov['coverage_percent']}% (minimum: {self.min_docstring_coverage}%)",
            })

        # Import cycles
        for cycle in results.get("import_cycles", {}).get("cycles", []):
            issues.append({
                "type": "import_cycle", "severity": "error",
                "value": " -> ".join(cycle),
                "message": f"Import cycle detected: {' -> '.join(cycle)}",
            })

        # Dead code
        for dc in results.get("dead_code", {}).get("dead_code", []):
            issues.append({
                "type": "dead_code", "severity": "warning",
                "file": dc["file"], "line": dc["line"], "value": dc.get("confidence", 0),
                "message": dc["message"],
            })

        # High churn files
        for churn_file in results.get("code_churn", {}).get("high_churn_files", []):
            issues.append({
                "type": "high_churn", "severity": "warning",
                "file": churn_file["file"],
                "value": f"{churn_file['commits']} commits, {churn_file['authors']} authors",
                "message": f"High churn file: {churn_file['file']} ({churn_file['commits']} commits by {churn_file['authors']} authors in 90 days)",
            })

        # JS/TS issues
        for js_issue in results.get("js_analysis", {}).get("issues", []):
            issues.append({
                "type": f"eslint_{js_issue.get('rule', 'unknown')}",
                "severity": js_issue.get("severity", "warning"),
                "file": js_issue["file"], "line": js_issue["line"],
                "message": js_issue["message"],
            })

        # Beartype issues
        if not results.get("beartype", {}).get("passed", True):
            for err in results.get("beartype", {}).get("errors", []):
                issues.append({"type": "runtime_type_error", "severity": "error", "message": err})

        return issues

    def _save_all_results(
        self, results: dict[str, Any], all_issues: list[dict]
    ) -> dict[str, Path]:
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
            "high_complexity_count": len([
                r for r in results.get("complexity", [])
                if r.get("complexity", 0) > self.complexity_threshold
            ]),
            "low_mi_count": len([
                r for r in results.get("maintainability", [])
                if r.get("mi", 100) < self.maintainability_threshold
            ]),
            "functions_too_long": len([
                i for i in results.get("function_issues", [])
                if i["issue_type"] == "TOO_LONG"
            ]),
            "functions_too_nested": len([
                i for i in results.get("function_issues", [])
                if i["issue_type"] == "TOO_NESTED"
            ]),
            "high_cognitive_count": len([
                r for r in results.get("cognitive", [])
                if r.get("exceeds_threshold")
            ]),
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
        """Generate comprehensive markdown summary."""
        metrics = self._compile_metrics(python_files, js_files, results, all_issues)
        tests = results.get("tests", {})
        type_cov = results.get("type_coverage", {})
        doc_cov = results.get("docstring_coverage", {})
        raw = results.get("raw_metrics", [])

        # Calculate raw totals
        total_loc = sum(r.get("loc", 0) for r in raw)
        total_sloc = sum(r.get("sloc", 0) for r in raw)
        total_comments = sum(r.get("comments", 0) for r in raw)

        lines = [
            "# Quality Analysis Report", "",
            "## Overview", "",
            f"**Files Analyzed**: {metrics['files_analyzed']} ({metrics['python_files']} Python, {metrics['js_files']} JS/TS)",
            f"**Functions Analyzed**: {metrics['total_functions']}",
            f"**Total Issues Found**: {metrics['issues_count']}",
            f"**Critical Issues**: {metrics['critical_issues']}", "",
            "## Code Metrics", "",
            f"- Total LOC: **{total_loc:,}**",
            f"- Source LOC (SLOC): **{total_sloc:,}**",
            f"- Comments: **{total_comments:,}**",
            f"- Comment Ratio: **{round(total_comments / total_sloc * 100, 1) if total_sloc > 0 else 0}%**", "",
            "## Quality Issues Summary", "",
            f"- Functions >50 lines: **{metrics['functions_too_long']}**",
            f"- High cyclomatic complexity (>{self.complexity_threshold}): **{metrics['high_complexity_count']}**",
            f"- High cognitive complexity (>{self.cognitive_complexity_threshold}): **{metrics['high_cognitive_count']}**",
            f"- Functions with nesting >{self.max_nesting_depth}: **{metrics['functions_too_nested']}**",
            f"- Code duplication blocks: **{metrics['duplicate_blocks']}**",
            f"- God objects: **{metrics['god_objects']}**",
            f"- Highly coupled modules: **{metrics['highly_coupled_modules']}**",
            f"- Import cycles: **{metrics['import_cycles']}**",
            f"- Dead code items: **{metrics['dead_code_items']}**", "",
            "## Coverage Metrics", "",
            f"- Type coverage: **{type_cov.get('coverage_percent', 0)}%** (minimum: {self.min_type_coverage}%)",
            f"- Docstring coverage: **{doc_cov.get('coverage_percent', 0)}%** (minimum: {self.min_docstring_coverage}%)", "",
            "## Test Suite Analysis", "",
            f"- Total tests: **{tests.get('total_tests', 0)}**",
            f"- Total assertions: **{tests.get('total_assertions', 0)}**",
            f"- Assertions per test: **{round(tests.get('total_assertions', 0) / tests.get('total_tests', 1), 1) if tests.get('total_tests', 0) > 0 else 0}**",
            f"- Unit tests: {tests.get('categories', {}).get('unit', 0)}",
            f"- Integration tests: {tests.get('categories', {}).get('integration', 0)}",
            f"- E2E tests: {tests.get('categories', {}).get('e2e', 0)}",
            f"- Test issues: **{len(tests.get('issues', []))}**", "",
            "## Runtime Type Checking (Beartype)", "",
            f"- Status: **{'✅ Passed' if metrics['beartype_passed'] else '❌ Failed'}**", "",
        ]

        # Critical issues
        critical_issues = [i for i in all_issues if i.get("severity") == "error"]
        if critical_issues:
            lines.extend(["## Critical Issues (Must Fix)", ""])
            for issue in critical_issues[:15]:
                file_info = f"`{issue.get('file', 'unknown')}`" if issue.get("file") else ""
                lines.append(f"- 🔴 {file_info}: {issue['message']}")
            if len(critical_issues) > 15:
                lines.append(f"- ... and {len(critical_issues) - 15} more critical issues")
            lines.append("")

        # Refactoring recommendations
        lines.extend(["## Refactoring Recommendations", ""])
        rec_num = 1
        if metrics["functions_too_long"] > 0:
            lines.append(f"{rec_num}. **Break Down Long Functions**: {metrics['functions_too_long']} functions exceed 50 lines")
            rec_num += 1
        if metrics["high_complexity_count"] > 0:
            lines.append(f"{rec_num}. **Reduce Cyclomatic Complexity**: {metrics['high_complexity_count']} functions exceed threshold")
            rec_num += 1
        if metrics["high_cognitive_count"] > 0:
            lines.append(f"{rec_num}. **Reduce Cognitive Complexity**: {metrics['high_cognitive_count']} functions are too complex")
            rec_num += 1
        if metrics["duplicate_blocks"] > 0:
            lines.append(f"{rec_num}. **Extract Duplicated Code**: {metrics['duplicate_blocks']} duplicate blocks found")
            rec_num += 1
        if metrics["god_objects"] > 0:
            lines.append(f"{rec_num}. **Refactor God Objects**: {metrics['god_objects']} classes need decomposition")
            rec_num += 1
        if metrics["import_cycles"] > 0:
            lines.append(f"{rec_num}. **Break Import Cycles**: {metrics['import_cycles']} cycles detected")
            rec_num += 1
        if type_cov.get("coverage_percent", 100) < self.min_type_coverage:
            lines.append(f"{rec_num}. **Add Type Annotations**: Coverage is {type_cov.get('coverage_percent', 0)}%")
            rec_num += 1
        if doc_cov.get("coverage_percent", 100) < self.min_docstring_coverage:
            lines.append(f"{rec_num}. **Add Docstrings**: Coverage is {doc_cov.get('coverage_percent', 0)}%")
            rec_num += 1
        if metrics["dead_code_items"] > 0:
            lines.append(f"{rec_num}. **Remove Dead Code**: {metrics['dead_code_items']} unused items found")
            rec_num += 1
        if metrics.get("high_churn_files", 0) > 0:
            lines.append(f"{rec_num}. **Review High Churn Files**: {metrics['high_churn_files']} files with frequent changes")
            rec_num += 1

        if metrics["issues_count"] == 0:
            lines.append("✅ No quality issues detected!")

        # Approval status
        lines.extend(["", "## Approval Status", ""])
        if metrics["critical_issues"] > 0:
            lines.append("**✗ Critical Issues Found** - Refactoring required before approval")
        elif metrics["issues_count"] > 0:
            lines.append("**⚠ Refactoring Recommended** - Non-critical issues found")
        else:
            lines.append("**✓ No Critical Issues** - Code quality acceptable")

        return "\n".join(lines)
