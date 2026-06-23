"""Cache Analysis Sub-Server.

Identifies caching opportunities using hybrid approach:
1. AST analysis - identify pure functions
2. Profiling cross-reference - find hot spots
3. Batch screening - filter by hit rate
4. Individual validation - measure precise impact
"""

import json
from pathlib import Path

from glintefy.config import get_config
from glintefy.subservers.base import BaseSubServer, SubServerResult
from glintefy.subservers.common.chunked_writer import cleanup_chunked_issues, write_chunked_issues
from glintefy.subservers.common.logging import debug_log, get_mcp_logger, log_debug, setup_logger
from glintefy.subservers.review.cache.batch_screener import BatchScreener
from glintefy.subservers.review.cache.hotspot_analyzer import HotspotAnalyzer
from glintefy.subservers.review.cache.individual_validator import IndividualValidator
from glintefy.subservers.review.cache.pure_function_detector import PureFunctionDetector
from glintefy.subservers.review.cache.summary_generator import (
    SummaryConfig,
    generate_issues,
    generate_summary,
)


class CacheSubServer(BaseSubServer):
    """Cache analysis sub-server."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        repo_path: Path,
        cache_size: int | None = None,
        hit_rate_threshold: float | None = None,
        speedup_threshold: float | None = None,
        min_calls: int | None = None,
        min_cumtime: float | None = None,
        test_timeout: int | None = None,
        num_runs: int | None = None,
        max_profile_age_hours: float | None = None,
        mcp_mode: bool = False,
    ):
        """Initialize cache sub-server.

        Args:
            input_dir: Input directory (scope results)
            output_dir: Output directory for cache analysis
            repo_path: Repository root path
            cache_size: LRU cache maxsize (default: 128)
            hit_rate_threshold: Minimum hit rate % (default: 20)
            speedup_threshold: Minimum speedup % (default: 5)
            min_calls: Minimum calls for hotspot (default: 100)
            min_cumtime: Minimum cumtime for hotspot (default: 0.1)
            test_timeout: Test suite timeout in seconds (default: 300)
            num_runs: Number of runs to average (default: 3)
            max_profile_age_hours: Max age for profile data in hours (default: 24)
            mcp_mode: Enable MCP logging mode
        """
        super().__init__(name="cache", input_dir=input_dir, output_dir=output_dir)

        self.repo_path = repo_path
        self.mcp_mode = mcp_mode
        self._logger = self._init_logger("cache", mcp_mode)

        # Load config
        config = get_config(start_dir=str(repo_path))
        cache_config = config.get("review", {}).get("cache", {})

        # Apply config with constructor overrides
        self.cache_size = cache_size or cache_config.get("cache_size", 128)
        self.hit_rate_threshold = hit_rate_threshold or cache_config.get("hit_rate_threshold", 20.0)
        self.remove_threshold = cache_config.get("remove_threshold", 10.0)
        self.size_adjustment_threshold = cache_config.get("size_adjustment_threshold", 50.0)
        self.min_suggested_maxsize = cache_config.get("min_suggested_maxsize", 16)
        self.speedup_threshold = speedup_threshold or cache_config.get("speedup_threshold", 5.0)
        self.min_calls = min_calls or cache_config.get("min_calls", 100)
        self.min_cumtime = min_cumtime or cache_config.get("min_cumtime", 0.1)
        self.test_timeout = test_timeout or cache_config.get("test_timeout", 300)
        self.num_runs = num_runs or cache_config.get("num_runs", 3)
        self.max_profile_age_hours = max_profile_age_hours or cache_config.get("max_profile_age_hours", 24.0)

        # Priority thresholds for hotspot analysis
        self.high_priority_calls = cache_config.get("high_priority_calls", 500)
        self.high_priority_time = cache_config.get("high_priority_time", 1.0)
        self.high_priority_indicators = cache_config.get("high_priority_indicators", 2)
        self.medium_priority_calls = cache_config.get("medium_priority_calls", 200)
        self.medium_priority_time = cache_config.get("medium_priority_time", 0.5)

        # Initialize analyzers
        self.pure_detector = PureFunctionDetector()
        self.hotspot_analyzer = HotspotAnalyzer(
            min_calls=self.min_calls,
            min_cumtime=self.min_cumtime,
            high_priority_calls=self.high_priority_calls,
            high_priority_time=self.high_priority_time,
            high_priority_indicators=self.high_priority_indicators,
            medium_priority_calls=self.medium_priority_calls,
            medium_priority_time=self.medium_priority_time,
        )
        self.batch_screener = BatchScreener(
            cache_size=self.cache_size,
            hit_rate_threshold=self.hit_rate_threshold,
            remove_threshold=self.remove_threshold,
            size_adjustment_threshold=self.size_adjustment_threshold,
            min_suggested_maxsize=self.min_suggested_maxsize,
            test_timeout=self.test_timeout,
            logger=self._logger,
        )
        self.individual_validator = IndividualValidator(
            cache_size=self.cache_size,
            speedup_threshold=self.speedup_threshold,
            test_timeout=self.test_timeout,
            num_runs=self.num_runs,
        )

    def _init_logger(self, name: str, mcp_mode: bool):
        """Initialize logger based on mode."""
        if mcp_mode:
            return get_mcp_logger(f"glintefy.{name}")
        return setup_logger(name, log_file=None, level=20)

    def _check_profile_freshness(self, prof_file: Path) -> tuple[bool, float, str]:
        """Check if profiling data is fresh enough to use.

        Args:
            prof_file: Path to the .prof file

        Returns:
            Tuple of (is_fresh, age_hours, warning_message)
            - is_fresh: True if file is within max_profile_age_hours
            - age_hours: Age of file in hours
            - warning_message: Warning if stale, empty string if fresh
        """
        import time

        if not prof_file.exists():
            return False, 0.0, ""

        file_mtime = prof_file.stat().st_mtime
        current_time = time.time()
        age_seconds = current_time - file_mtime
        age_hours = age_seconds / 3600

        if age_hours > self.max_profile_age_hours:
            warning = (
                f"Profile data is {age_hours:.1f} hours old "
                f"(threshold: {self.max_profile_age_hours} hours). "
                f"Delete with: `python -m glintefy review clean -s profile` "
                f"then regenerate with: `python -m glintefy review profile -- pytest tests/`"
            )
            return False, age_hours, warning

        return True, age_hours, ""

    def _validate_profile_against_code(
        self,
        prof_file: Path,
        python_files: list[Path],
    ) -> tuple[int, int, list[str]]:
        """Validate that profiled functions exist in current codebase.

        Compares functions in the profile data against actual functions in the code
        to detect if the profile is outdated (profiled functions no longer exist).

        Args:
            prof_file: Path to the .prof file
            python_files: List of Python files in the codebase

        Returns:
            Tuple of (matched_count, orphan_count, orphan_warnings)
            - matched_count: Functions found in both profile and code
            - orphan_count: Functions in profile but not in code
            - orphan_warnings: Warning messages for orphaned functions
        """
        import ast
        import pstats

        if not prof_file.exists():
            return 0, 0, []

        # Load profile stats
        try:
            stats = pstats.Stats(str(prof_file))
        except Exception:
            return 0, 0, []

        # Extract function names and files from profile
        profiled_functions = set()
        for (filename, _line, func_name), _ in stats.stats.items():
            # Skip builtins and libraries
            if "<" in filename or "site-packages" in filename:
                continue
            if "/lib/python" in filename or "/lib64/python" in filename:
                continue
            profiled_functions.add((Path(filename).name, func_name))

        if not profiled_functions:
            return 0, 0, []

        # Extract function names from current code
        current_functions = set()
        for py_file in python_files:
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        current_functions.add((py_file.name, node.name))
            except Exception:
                continue

        # Find matches and orphans
        matched = profiled_functions & current_functions
        orphans = profiled_functions - current_functions

        # Generate warnings for orphaned functions (max 5)
        orphan_warnings = []
        for filename, func_name in list(orphans)[:5]:
            orphan_warnings.append(f"Profiled function '{func_name}' in '{filename}' no longer exists in codebase")

        if len(orphans) > 5:
            orphan_warnings.append(f"... and {len(orphans) - 5} more orphaned functions")

        return len(matched), len(orphans), orphan_warnings

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for cache analysis.

        Returns:
            Tuple of (valid, missing_files)
        """
        missing = []

        # Check for files to analyze
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            missing.append(f"No files list found at {files_list}. Run scope sub-server first.")

        # Check for profiling data (optional but recommended)
        prof_file = self.input_dir.parent / "perf" / "test_profile.prof"
        if not prof_file.exists():
            # Not a blocker, just a warning
            pass

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute cache analysis - wrapper for run()."""
        return self.run()

    @debug_log(get_mcp_logger("glintefy.subservers.review.cache"))
    def run(self) -> SubServerResult:
        """Run cache analysis pipeline."""
        log_debug(self._logger, "Starting cache analysis")

        try:
            # Stage 1: Identify pure functions and existing caches
            pure_candidates, existing_caches, python_files = self._identify_pure_functions()
            log_debug(self._logger, f"Found {len(pure_candidates)} pure function candidates")
            log_debug(self._logger, f"Found {len(existing_caches)} existing caches")

            # Stage 1B: Evaluate existing caches
            existing_evaluations = []
            if existing_caches:
                existing_evaluations = self._evaluate_existing_caches(existing_caches)
                log_debug(self._logger, f"Evaluated {len(existing_evaluations)} existing caches")

            # Stage 2: Cross-reference with profiling data
            cache_candidates, profile_warnings = self._cross_reference_hotspots(pure_candidates, python_files)
            log_debug(self._logger, f"Found {len(cache_candidates)} cache candidates (pure + hot)")

            if not cache_candidates and not existing_evaluations:
                return self._create_empty_result(
                    "No cache candidates found (no pure functions that are also hotspots) and no existing caches to evaluate",
                    pure_candidates=pure_candidates,
                    profile_warnings=profile_warnings,
                )

            # Stage 3A: Batch screening (only for new candidates)
            screening_results = []
            validation_results = []
            if cache_candidates:
                screening_results = self._batch_screen(cache_candidates)
                survivors = [r for r in screening_results if r.passed_screening]
                log_debug(self._logger, f"Batch screening: {len(survivors)}/{len(cache_candidates)} passed")

                # Stage 3B: Individual validation
                if survivors:
                    validation_results = self._individual_validate(screening_results)
                    recommendations = [r for r in validation_results if r.recommendation == "APPLY"]
                    log_debug(self._logger, f"Individual validation: {len(recommendations)} recommended")

            # Generate outputs
            return self._create_final_result(
                pure_candidates,
                cache_candidates,
                screening_results,
                validation_results,
                existing_evaluations,
                profile_warnings=profile_warnings,
            )

        except Exception as e:
            self._logger.error(f"Cache analysis failed: {e}", exc_info=True)
            return SubServerResult(
                status="FAILED",
                summary=f"# Cache Analysis Failed\n\nError: {e}",
                metrics={},
                artifacts={},
                errors=[str(e)],
            )

    def _identify_pure_functions(self) -> tuple[list, list, list[Path]]:
        """Stage 1: AST-based pure function detection.

        Returns:
            Tuple of (new_candidates, existing_caches, python_files)
        """
        # Read files from scope
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return ([], [], [])

        python_files = []
        for line in files_list.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            path = Path(line)
            if path.suffix == ".py" and path.exists():
                python_files.append(path)

        # Analyze each file
        all_new_candidates = []
        all_existing_caches = []
        for file_path in python_files:
            new_candidates, existing_caches = self.pure_detector.analyze_file(file_path)
            all_new_candidates.extend(new_candidates)
            all_existing_caches.extend(existing_caches)

        return (all_new_candidates, all_existing_caches, python_files)

    def _cross_reference_hotspots(
        self,
        pure_candidates: list,
        python_files: list[Path],
    ) -> tuple[list, list[str]]:
        """Stage 2: Cross-reference with profiling data.

        Args:
            pure_candidates: Pure function candidates from AST analysis
            python_files: List of Python files in the codebase

        Returns:
            Tuple of (cache_candidates, warnings)
            - cache_candidates: List of candidates that are pure AND hot
            - warnings: List of warning messages (stale profile, orphaned functions)
        """
        prof_file = self.input_dir.parent / "perf" / "test_profile.prof"
        warnings = []

        if not prof_file.exists():
            log_debug(self._logger, f"No profiling data found at {prof_file}")
            return [], []

        # Check profile age freshness
        is_fresh, age_hours, stale_warning = self._check_profile_freshness(prof_file)
        if not is_fresh:
            self._logger.warning(stale_warning)
            warnings.append(stale_warning)

        log_debug(self._logger, f"Profile data age: {age_hours:.1f} hours (fresh: {is_fresh})")

        # Check profile data matches current code
        matched, orphans, orphan_warnings = self._validate_profile_against_code(prof_file, python_files)
        if orphans > 0:
            orphan_summary = f"Profile contains {orphans} functions that no longer exist in codebase (matched: {matched}). Profile may be outdated."
            self._logger.warning(orphan_summary)
            warnings.append(orphan_summary)
            warnings.extend(orphan_warnings)

        log_debug(self._logger, f"Profile validation: {matched} matched, {orphans} orphaned")

        hotspots = self.hotspot_analyzer.analyze_profile(prof_file)
        log_debug(self._logger, f"Found {len(hotspots)} hotspots from profiling")

        cache_candidates = self.hotspot_analyzer.cross_reference(
            pure_candidates,
            hotspots,
        )

        return cache_candidates, warnings

    def _batch_screen(self, candidates: list) -> list:
        """Stage 3A: Batch screening."""
        log_debug(self._logger, f"Starting batch screening for {len(candidates)} candidates")
        results = self.batch_screener.screen_candidates(
            candidates,
            self.repo_path,
        )
        return results

    def _individual_validate(self, screening_results: list) -> list:
        """Stage 3B: Individual validation."""
        survivors = [r for r in screening_results if r.passed_screening]
        log_debug(self._logger, f"Starting individual validation for {len(survivors)} survivors")
        results = self.individual_validator.validate_candidates(
            screening_results,
            self.repo_path,
        )
        return results

    def _evaluate_existing_caches(self, existing_caches: list) -> list:
        """Stage 1B: Evaluate existing cache decorators."""
        log_debug(self._logger, f"Evaluating {len(existing_caches)} existing caches")
        results = self.batch_screener.evaluate_existing_caches(
            existing_caches,
            self.repo_path,
        )
        return results

    def _save_base_analysis(
        self,
        pure_count=0,
        candidates_count=0,
        screened_count=0,
        passed_count=0,
        validated_count=0,
        recs_count=0,
        existing_count=0,
        keep_count=0,
        remove_count=0,
        adjust_count=0,
    ) -> dict:
        """Save base analysis file and return artifacts dict."""
        artifacts = {}

        # Always save analysis file
        analysis_file = self.output_dir / "cache_analysis.json"
        analysis_data = {
            "pure_functions_count": pure_count,
            "cache_candidates_count": candidates_count,
            "batch_screened": screened_count,
            "batch_passed": passed_count,
            "validated_count": validated_count,
            "recommendations_count": recs_count,
            "existing_caches_count": existing_count,
            "existing_keep_count": keep_count,
            "existing_remove_count": remove_count,
            "existing_adjust_count": adjust_count,
            "thresholds": {
                "hit_rate_threshold": self.hit_rate_threshold,
                "speedup_threshold": self.speedup_threshold,
                "min_calls": self.min_calls,
                "min_cumtime": self.min_cumtime,
            },
        }
        analysis_file.write_text(json.dumps(analysis_data, indent=2))
        artifacts["analysis"] = analysis_file

        return artifacts

    def _create_empty_result(
        self,
        reason: str,
        pure_candidates: list = None,
        profile_warnings: list[str] | None = None,
    ) -> SubServerResult:
        """Create result when no candidates found."""
        pure_candidates = pure_candidates or []
        profile_warnings = profile_warnings or []
        pure_count = len([c for c in pure_candidates if c.is_pure])

        summary = f"# Cache Analysis\n\n{reason}"
        if pure_count > 0:
            summary += f"\n\n**Found {pure_count} pure functions**, but none were identified as hot spots by profiling."

        if profile_warnings:
            summary += "\n\n## Profile Warnings\n"
            for warning in profile_warnings:
                summary += f"\n> [WARN] {warning}"

        # Save base analysis file
        artifacts = self._save_base_analysis(pure_count=pure_count)

        return SubServerResult(
            status="SUCCESS",
            summary=summary,
            metrics={
                "pure_functions": pure_count,
                "cache_candidates": 0,
                "batch_passed": 0,
                "recommendations": 0,
            },
            artifacts=artifacts,
            errors=[],
        )

    def _create_screening_result(self, screening_results: list) -> SubServerResult:
        """Create result when screening filtered all candidates."""
        summary = f"# Cache Analysis\n\n{len(screening_results)} candidates screened, none passed hit rate threshold ({self.hit_rate_threshold}%)."

        # Save base analysis file
        artifacts = self._save_base_analysis(
            screened_count=len(screening_results),
            candidates_count=len(screening_results),
        )

        return SubServerResult(
            status="SUCCESS",
            summary=summary,
            metrics={
                "cache_candidates": len(screening_results),
                "batch_passed": 0,
                "recommendations": 0,
            },
            artifacts=artifacts,
            errors=[],
        )

    def _create_final_result(
        self,
        pure_candidates: list,
        cache_candidates: list,
        screening_results: list,
        validation_results: list,
        existing_evaluations: list,
        profile_warnings: list[str] | None = None,
    ) -> SubServerResult:
        """Create final result with all data."""
        recommendations = [r for r in validation_results if r.recommendation == "APPLY"]

        # Generate summary
        summary = self._generate_summary(
            pure_candidates,
            cache_candidates,
            screening_results,
            validation_results,
            existing_evaluations,
            profile_warnings=profile_warnings or [],
        )

        # Save artifacts
        artifacts = self._save_artifacts(
            pure_candidates,
            cache_candidates,
            screening_results,
            validation_results,
            existing_evaluations,
        )

        status = "SUCCESS" if len(recommendations) > 0 or len(existing_evaluations) > 0 else "PARTIAL"

        return SubServerResult(
            status=status,
            summary=summary,
            metrics={
                "pure_functions": len([c for c in pure_candidates if c.is_pure]),
                "cache_candidates": len(cache_candidates),
                "batch_screened": len(screening_results),
                "batch_passed": len([r for r in screening_results if r.passed_screening]),
                "validated": len(validation_results),
                "recommendations": len(recommendations),
                "existing_caches": len(existing_evaluations),
                "existing_keep": len([e for e in existing_evaluations if e.recommendation == "KEEP"]),
                "existing_remove": len([e for e in existing_evaluations if e.recommendation == "REMOVE"]),
                "existing_adjust": len([e for e in existing_evaluations if e.recommendation == "ADJUST_SIZE"]),
            },
            artifacts=artifacts,
            errors=[],
        )

    def _generate_summary(
        self,
        pure,
        candidates,
        screening,
        validation,
        existing_evals,
        profile_warnings: list[str] | None = None,
    ) -> str:
        """Generate markdown summary.

        Delegates to summary_generator module for cleaner separation.
        """
        config = SummaryConfig(
            cache_size=self.cache_size,
            hit_rate_threshold=self.hit_rate_threshold,
            speedup_threshold=self.speedup_threshold,
        )
        return generate_summary(
            pure=pure,
            candidates=candidates,
            screening=screening,
            validation=validation,
            existing_evals=existing_evals,
            config=config,
            profile_warnings=profile_warnings,
        )

    def _generate_issues(self, validation, existing_evals) -> list[dict]:
        """Convert cache analysis results to issues for the report.

        Delegates to summary_generator module for cleaner separation.
        """
        return generate_issues(validation, existing_evals, self.cache_size)

    def _save_artifacts(self, pure, candidates, screening, validation, existing_evals) -> dict:
        """Save all artifacts to output directory."""
        # Calculate counts
        recommendations = [r for r in validation if r.recommendation == "APPLY"]
        pure_count = len([c for c in pure if c.is_pure])
        screened_count = len(screening)
        passed_count = len([r for r in screening if r.passed_screening]) if screening else 0

        # Save base analysis file
        artifacts = self._save_base_analysis(
            pure_count=pure_count,
            candidates_count=len(candidates),
            screened_count=screened_count,
            passed_count=passed_count,
            validated_count=len(validation),
            recs_count=len(recommendations),
            existing_count=len(existing_evals),
            keep_count=len([e for e in existing_evals if e.recommendation == "KEEP"]),
            remove_count=len([e for e in existing_evals if e.recommendation == "REMOVE"]),
            adjust_count=len([e for e in existing_evals if e.recommendation == "ADJUST_SIZE"]),
        )

        # Save recommendations as JSON
        if recommendations:
            recs_file = self.output_dir / "cache_recommendations.json"
            recs_data = [
                {
                    "file": str(r.candidate.file_path),
                    "function": r.candidate.function_name,
                    "line": r.candidate.line_number,
                    "module": r.candidate.module_path,
                    "decorator": f"@lru_cache(maxsize={self.cache_size})",
                    "speedup_percent": round(r.speedup_percent, 2),
                    "hit_rate_percent": round(r.hit_rate, 2),
                    "evidence": {
                        "hits": r.hits,
                        "misses": r.misses,
                        "baseline_time": round(r.baseline_time, 4),
                        "cached_time": round(r.cached_time, 4),
                    },
                }
                for r in recommendations
            ]
            recs_file.write_text(json.dumps(recs_data, indent=2))
            artifacts["recommendations"] = recs_file

        # Save existing cache evaluations as JSON
        if existing_evals:
            existing_file = self.output_dir / "existing_cache_evaluations.json"
            existing_data = [
                {
                    "file": str(e.candidate.file_path),
                    "function": e.candidate.function_name,
                    "line": e.candidate.line_number,
                    "module": e.candidate.module_path,
                    "current_maxsize": e.candidate.current_maxsize if e.candidate.current_maxsize >= 0 else "unbounded",
                    "hit_rate_percent": round(e.hit_rate, 2),
                    "recommendation": e.recommendation,
                    "reason": e.reason,
                    "suggested_maxsize": e.suggested_maxsize,
                    "evidence": {
                        "hits": e.hits,
                        "misses": e.misses,
                    },
                }
                for e in existing_evals
            ]
            existing_file.write_text(json.dumps(existing_data, indent=2))
            artifacts["existing_evaluations"] = existing_file

        # Generate and save issues in chunked format
        all_issues = self._generate_issues(validation, existing_evals)
        if all_issues:
            # Get report directory (parent of output_dir / "report")
            report_dir = self.output_dir.parent / "report"

            # Get unique issue types
            issue_types = list({issue.get("type", "unknown") for issue in all_issues})

            # Cleanup old chunked files for these issue types
            cleanup_chunked_issues(
                output_dir=report_dir,
                issue_types=issue_types,
                prefix="issues",
            )

            # Write chunked issues
            written_files = write_chunked_issues(
                issues=all_issues,
                output_dir=report_dir,
                prefix="issues",
            )

            if written_files:
                artifacts["issues"] = written_files[0]  # First chunk for reference

        return artifacts
