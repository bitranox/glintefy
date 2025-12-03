"""Batch cache screening.

Tests all candidates simultaneously to filter by cache hit rate.
This is the FAST phase that eliminates obvious losers.

Uses temporary source modification instead of monkey-patching because:
- subprocess.run() creates fresh Python interpreter
- Fresh interpreter imports from disk, not parent's memory
- Source modifications persist across process boundary
"""

import importlib
import os
from pathlib import Path
from typing import Any

from glintefy.config import get_subserver_config, get_tool_config
from glintefy.subservers.review.cache.cache_models import (
    BatchScreeningResult,
    CacheCandidate,
    ExistingCacheCandidate,
    ExistingCacheEvaluation,
)
from glintefy.subservers.review.cache.source_patcher import SourcePatcher


class BatchScreener:
    """Screen cache candidates in batch for hit rate."""

    def __init__(
        self,
        cache_size: int = 128,
        hit_rate_threshold: float = 20.0,
        remove_threshold: float = 10.0,
        size_adjustment_threshold: float = 50.0,
        min_suggested_maxsize: int = 16,
        test_timeout: int = 300,
        logger: Any | None = None,
    ):
        """Initialize batch screener.

        Args:
            cache_size: LRU cache maxsize
            hit_rate_threshold: Minimum hit rate percentage to pass screening
            remove_threshold: Hit rate below this recommends removal
            size_adjustment_threshold: Cache usage below this % triggers size adjustment
            min_suggested_maxsize: Minimum suggested maxsize when reducing
            test_timeout: Test suite timeout in seconds
            logger: Logger instance for debugging
        """
        self.cache_size = cache_size
        self.hit_rate_threshold = hit_rate_threshold
        self.remove_threshold = remove_threshold
        self.size_adjustment_threshold = size_adjustment_threshold
        self.min_suggested_maxsize = min_suggested_maxsize
        self.test_timeout = test_timeout
        self.logger = logger
        self.patcher = None  # Created in screen_candidates()

    def screen_candidates(
        self,
        candidates: list[CacheCandidate],
        repo_path: Path,
    ) -> list[BatchScreeningResult]:
        """Screen all candidates in a single test run.

        Args:
            candidates: Cache candidates to test
            repo_path: Repository root path

        Returns:
            Screening results for each candidate
        """
        if not candidates:
            return []

        # Create patcher and start session (backs up files for safe modification)
        self.patcher = SourcePatcher(repo_path=repo_path)

        success, _error = self.patcher.start()
        if not success:
            # Failed to start (path doesn't exist, etc.)
            return []

        try:
            # Apply caches to source files
            applied_count = self._apply_caches(candidates)

            if applied_count == 0:
                return []

            # Run test suite ONCE (subprocess sees modified source files)
            test_passed = self._run_test_suite(repo_path)

            if not test_passed:
                # Tests failed - can't collect stats
                return []

            # Import modified modules and collect cache statistics
            results = self._collect_cache_stats(candidates)

            return results

        finally:
            # Always restore original files
            self.patcher.end()

    def _apply_caches(self, candidates: list[CacheCandidate]) -> int:
        """Apply LRU cache decorators to source files.

        Returns:
            Number of caches successfully applied
        """
        applied_count = 0

        for candidate in candidates:
            success = self.patcher.apply_cache_decorator(
                file_path=candidate.file_path,
                function_name=candidate.function_name,
                cache_size=self.cache_size,
            )

            if success:
                applied_count += 1

        return applied_count

    def _analyze_cache_usage_statically(
        self,
        candidate: ExistingCacheCandidate,
        repo_path: Path,
    ) -> tuple[str, str, int | None]:
        """Analyze cache usage through static code analysis.

        Instead of running code, analyze the codebase to predict cache benefit
        by counting call sites in production code.

        Returns:
            (recommendation, reason, suggested_maxsize)
        """

        call_count = self._count_function_calls(candidate.function_name, repo_path)

        if call_count == 0:
            return ("REMOVE", "Function not called in production code (only in tests)", None)
        if call_count == 1:
            return ("REMOVE", f"Function called only {call_count} time in codebase - no cache benefit", None)
        if call_count >= 2:
            return ("KEEP", f"Function called {call_count} times in codebase - likely benefits from caching", None)

        return ("KEEP", "Insufficient data to determine", None)

    def _get_exclude_patterns(self) -> list[str]:
        """Get exclude patterns from config.

        Extracts directory names from glob patterns like '**/.venv/*' -> '.venv'.
        """
        scope_config = get_subserver_config("scope")
        glob_patterns = scope_config.get("exclude_patterns", [])

        # Extract directory names from glob patterns
        # e.g., "**/.venv/*" -> ".venv", "**/node_modules/*" -> "node_modules"
        excludes = []
        for pattern in glob_patterns:
            # Remove glob wildcards and extract path components
            parts = pattern.replace("**", "").replace("*", "").strip("/").split("/")
            for part in parts:
                if (part and not part.startswith(".")) or (part.startswith(".") and len(part) > 1):
                    excludes.append(part)

        # Fallback if config is empty
        if not excludes:
            excludes = [
                ".venv",
                "venv",
                ".env",
                "env",
                ".virtualenv",
                "virtualenv",
                "node_modules",
                "__pycache__",
                ".tox",
                ".nox",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "dist",
                "build",
                ".git",
                ".egg-info",
            ]

        return excludes

    def _should_exclude_path(self, path: Path) -> bool:
        """Check if path should be excluded from scanning."""
        path_str = str(path)
        exclude_patterns = self._get_exclude_patterns()
        return any(excl in path_str for excl in exclude_patterns)

    def _count_function_calls(self, function_name: str, repo_path: Path) -> int:
        """Count how many times a function is called in production code.

        Args:
            function_name: Name of the function to search for
            repo_path: Repository root path

        Returns:
            Number of call sites found
        """
        import ast

        call_count = 0

        for py_file in repo_path.rglob("*.py"):
            # Skip test files and excluded directories
            if "test" in str(py_file).lower():
                continue
            if self._should_exclude_path(py_file):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue

                    func_name = self._extract_called_function_name(node)
                    if func_name == function_name:
                        call_count += 1

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        return call_count

    def _extract_called_function_name(self, call_node) -> str | None:
        """Extract function name from a Call AST node.

        Args:
            call_node: AST Call node

        Returns:
            Function name or None if not extractable
        """
        import ast

        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        if isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    def _run_test_suite(self, repo_path: Path) -> bool:
        """Run pytest test suite in-process to preserve cache statistics.

        Returns:
            True if tests passed
        """
        try:
            import pytest

            # Get pytest config settings
            pytest_config = get_tool_config("pytest")
            testpaths = pytest_config.get("testpaths", ["tests"])
            test_path = testpaths[0] if testpaths else "tests"

            # Save current directory
            old_cwd = Path.cwd()

            try:
                # Change to repo directory
                os.chdir(repo_path)

                # Build pytest args from config
                pytest_args = [
                    test_path,
                    "-q",
                    "--tb=no",
                    "-p",
                    "no:warnings",  # Suppress warnings
                    "-p",
                    "no:cacheprovider",  # Disable pytest cache
                ]

                # Add disabled plugins from config
                disabled_plugins = pytest_config.get("disabled_plugins", [])
                for plugin in disabled_plugins:
                    pytest_args.extend(["-p", f"no:{plugin}"])

                # Run pytest in-process (preserves cache stats)
                exit_code = pytest.main(pytest_args)

                if self.logger and exit_code != 0:
                    self.logger.debug(f"pytest.main() returned exit code: {exit_code}")

                return exit_code == 0

            finally:
                # Restore directory
                os.chdir(old_cwd)

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Exception running test suite: {e}")
            return False

    def _collect_cache_stats(self, candidates: list[CacheCandidate]) -> list[BatchScreeningResult]:
        """Import modified modules and collect cache statistics.

        Args:
            candidates: Candidates that were cached

        Returns:
            Screening results with cache statistics
        """
        results = []

        for candidate in candidates:
            try:
                # Import module (now has @lru_cache decorator)
                # Force reload to get modified version
                module = importlib.import_module(candidate.module_path)
                importlib.reload(module)

                # Get cached function
                cached_func = getattr(module, candidate.function_name)

                # Get cache statistics
                cache_info = cached_func.cache_info()

                hit_rate = self._calculate_hit_rate(cache_info.hits, cache_info.misses)
                passed = hit_rate >= self.hit_rate_threshold

                results.append(
                    BatchScreeningResult(
                        candidate=candidate,
                        hits=cache_info.hits,
                        misses=cache_info.misses,
                        hit_rate=hit_rate,
                        maxsize=cache_info.maxsize,
                        currsize=cache_info.currsize,
                        passed_screening=passed,
                    )
                )

            except Exception:
                # If import or cache_info fails, skip candidate
                continue

        return results

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0

    def evaluate_existing_caches(
        self,
        existing_caches: list[ExistingCacheCandidate],
        repo_path: Path,
    ) -> list[ExistingCacheEvaluation]:
        """Evaluate existing @lru_cache decorators.

        Tries runtime analysis first, falls back to static code analysis.

        Args:
            existing_caches: Functions with existing cache decorators
            repo_path: Repository root path

        Returns:
            Evaluations for each existing cache
        """
        if not existing_caches:
            return []

        results = []
        for candidate in existing_caches:
            evaluation = self._evaluate_single_cache(candidate, repo_path)
            if evaluation:
                results.append(evaluation)

        return results

    def _evaluate_single_cache(
        self,
        candidate: ExistingCacheCandidate,
        repo_path: Path,
    ) -> ExistingCacheEvaluation | None:
        """Evaluate a single existing cache decorator.

        Args:
            candidate: Cache candidate to evaluate
            repo_path: Repository root path

        Returns:
            Evaluation result or None if evaluation failed
        """
        try:
            cached_func = self._resolve_cached_function(candidate)

            if cached_func is None:
                return self._create_static_analysis_result(candidate, repo_path)

            return self._create_runtime_analysis_result(candidate, cached_func, repo_path)

        except (ImportError, ModuleNotFoundError) as e:
            if self.logger:
                self.logger.warning(f"Failed to import module {candidate.module_path}: {e}")
            return None

    def _resolve_cached_function(self, candidate: ExistingCacheCandidate):
        """Resolve a cached function from its module.

        Handles module-level functions and class methods (including private).

        Args:
            candidate: Cache candidate with module and function info

        Returns:
            The cached function or None if not found
        """
        module = importlib.import_module(candidate.module_path)

        # Try module-level function first
        cached_func = getattr(module, candidate.function_name, None)
        if cached_func is not None:
            return cached_func

        # Search class methods
        return self._find_method_in_classes(module, candidate.function_name)

    def _find_method_in_classes(self, module, function_name: str):
        """Find a method in any class within a module.

        Args:
            module: The imported module
            function_name: Name of the method to find

        Returns:
            The method or None if not found
        """
        for name in dir(module):
            obj = getattr(module, name)
            if not isinstance(obj, type):
                continue

            # Try direct attribute access
            if hasattr(obj, function_name):
                return getattr(obj, function_name)

            # Try name-mangled private methods (_ClassName__method)
            if function_name.startswith("_"):
                mangled_name = f"_{obj.__name__}{function_name}"
                if hasattr(obj, mangled_name):
                    return getattr(obj, mangled_name)

        return None

    def _create_static_analysis_result(
        self,
        candidate: ExistingCacheCandidate,
        repo_path: Path,
    ) -> ExistingCacheEvaluation:
        """Create evaluation result using static code analysis.

        Args:
            candidate: Cache candidate to analyze
            repo_path: Repository root path

        Returns:
            Evaluation based on static analysis
        """
        if self.logger:
            self.logger.debug(f"Using static analysis for {candidate.function_name}")

        recommendation, reason, suggested_maxsize = self._analyze_cache_usage_statically(candidate, repo_path)

        return ExistingCacheEvaluation(
            candidate=candidate,
            hits=0,
            misses=0,
            hit_rate=0.0,
            recommendation=recommendation,
            reason=f"Static analysis: {reason}",
            suggested_maxsize=suggested_maxsize,
        )

    def _create_runtime_analysis_result(
        self,
        candidate: ExistingCacheCandidate,
        cached_func,
        repo_path: Path,
    ) -> ExistingCacheEvaluation:
        """Create evaluation result using runtime cache statistics.

        Args:
            candidate: Cache candidate
            cached_func: The resolved cached function
            repo_path: Repository root path

        Returns:
            Evaluation based on runtime data or fallback to static analysis
        """
        cache_info = cached_func.cache_info()

        if self.logger:
            self.logger.debug(
                f"Cache stats for {candidate.function_name}: "
                f"hits={cache_info.hits}, misses={cache_info.misses}, "
                f"currsize={cache_info.currsize}, maxsize={cache_info.maxsize}"
            )

        total_calls = cache_info.hits + cache_info.misses

        if total_calls == 0:
            return self._create_static_analysis_result(candidate, repo_path)

        return self._create_production_data_result(candidate, cache_info)

    def _create_production_data_result(
        self,
        candidate: ExistingCacheCandidate,
        cache_info,
    ) -> ExistingCacheEvaluation:
        """Create evaluation result from production cache data.

        Args:
            candidate: Cache candidate
            cache_info: Cache statistics from lru_cache

        Returns:
            Evaluation based on production hit/miss data
        """
        hit_rate = self._calculate_hit_rate(cache_info.hits, cache_info.misses)

        if self.logger:
            self.logger.info(
                f"Using production cache data for {candidate.function_name}: {cache_info.hits} hits, {cache_info.misses} misses ({hit_rate:.1f}% hit rate)"
            )

        recommendation, reason, suggested_maxsize = self._evaluate_cache_effectiveness(
            hit_rate=hit_rate,
            current_maxsize=candidate.current_maxsize,
            currsize=cache_info.currsize,
        )

        return ExistingCacheEvaluation(
            candidate=candidate,
            hits=cache_info.hits,
            misses=cache_info.misses,
            hit_rate=hit_rate,
            recommendation=recommendation,
            reason=f"Production data: {reason}",
            suggested_maxsize=suggested_maxsize,
        )

    def _evaluate_cache_effectiveness(
        self,
        hit_rate: float,
        current_maxsize: int,
        currsize: int,
    ) -> tuple[str, str | None, int | None]:
        """Evaluate cache effectiveness and make recommendation.

        Args:
            hit_rate: Cache hit rate percentage
            current_maxsize: Current maxsize setting (-1 for unbounded)
            currsize: Current cache size

        Returns:
            (recommendation, reason, suggested_maxsize)
        """
        # Low hit rate - remove cache
        if hit_rate < self.remove_threshold:
            return (
                "REMOVE",
                f"Very low hit rate ({hit_rate:.1f}%) - cache not beneficial",
                None,
            )

        # Acceptable hit rate - keep cache
        if hit_rate >= self.hit_rate_threshold:
            # Check if maxsize is too large (cache not filling up)
            usage_ratio = (currsize / current_maxsize * 100) if current_maxsize > 0 else 100
            if current_maxsize > 0 and usage_ratio < self.size_adjustment_threshold:
                # Cache using less than threshold% of allocated size - suggest reducing
                suggested = max(self.min_suggested_maxsize, currsize * 2)  # 2x current usage, minimum from config
                return (
                    "ADJUST_SIZE",
                    f"Good hit rate ({hit_rate:.1f}%) but maxsize too large (using {currsize}/{current_maxsize}) - can reduce",
                    suggested,
                )

            # Cache is working well
            return (
                "KEEP",
                f"Good hit rate ({hit_rate:.1f}%)",
                None,
            )

        # Marginal hit rate (between remove_threshold and hit_rate_threshold)
        return (
            "KEEP",
            f"Marginal hit rate ({hit_rate:.1f}%) - monitor performance",
            None,
        )
