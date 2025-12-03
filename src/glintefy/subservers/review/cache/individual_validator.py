"""Individual cache validation.

Tests each surviving candidate individually to measure precise impact.
This is the SLOW phase that provides accurate measurements.

Uses temporary source modification instead of monkey-patching because:
- subprocess.run() creates fresh Python interpreter
- Fresh interpreter imports from disk, not parent's memory
- Source modifications persist across process boundary
"""

import importlib
import subprocess
import sys
import time
from pathlib import Path

from glintefy.config import get_tool_config
from glintefy.subservers.review.cache.cache_models import BatchScreeningResult, IndividualValidationResult
from glintefy.subservers.review.cache.source_patcher import SourcePatcher


class IndividualValidator:
    """Validate cache candidates individually for precise measurements."""

    def __init__(
        self,
        cache_size: int = 128,
        speedup_threshold: float = 5.0,
        test_timeout: int = 300,
        num_runs: int = 3,
    ):
        """Initialize individual validator.

        Args:
            cache_size: LRU cache maxsize
            speedup_threshold: Minimum speedup percentage to recommend
            test_timeout: Test suite timeout in seconds
            num_runs: Number of runs to average (for stability)
        """
        self.cache_size = cache_size
        self.speedup_threshold = speedup_threshold
        self.test_timeout = test_timeout
        self.num_runs = num_runs

    def validate_candidates(
        self,
        screening_results: list[BatchScreeningResult],
        repo_path: Path,
    ) -> list[IndividualValidationResult]:
        """Validate each candidate individually.

        Args:
            screening_results: Results from batch screening (survivors only)
            repo_path: Repository root path

        Returns:
            Validation results for each candidate
        """
        # Filter to only survivors
        survivors = [r for r in screening_results if r.passed_screening]

        results = []

        # Create patcher and start session (ONE branch for all candidate tests)
        patcher = SourcePatcher(repo_path=repo_path)
        success, _error = patcher.start()

        if not success:
            # Failed to create branch - return empty results
            return results

        try:
            for screening_result in survivors:
                candidate = screening_result.candidate

                # Measure baseline (without cache)
                baseline_time = self._measure_baseline(repo_path)

                if baseline_time is None:
                    # Test suite failed - skip this candidate
                    continue

                # Measure with cache (uses file backup within the branch)
                cached_time, cache_info = self._measure_with_cache(candidate, repo_path, patcher)

                if cached_time is None or cache_info is None:
                    # Test suite failed - skip this candidate
                    continue

                # Calculate metrics
                speedup = self._calculate_speedup(baseline_time, cached_time)
                hit_rate = self._calculate_hit_rate(cache_info.hits, cache_info.misses)

                # Determine recommendation
                recommendation, reason = self._make_recommendation(speedup, hit_rate)

                results.append(
                    IndividualValidationResult(
                        candidate=candidate,
                        baseline_time=baseline_time,
                        cached_time=cached_time,
                        speedup_percent=speedup,
                        hits=cache_info.hits,
                        misses=cache_info.misses,
                        hit_rate=hit_rate,
                        recommendation=recommendation,
                        rejection_reason=reason,
                    )
                )

            return results

        finally:
            # Delete branch and restore original
            patcher.end()

    def _build_pytest_command(self) -> list[str]:
        """Build pytest command from config settings.

        Returns:
            Command list for subprocess
        """
        pytest_config = get_tool_config("pytest")
        testpaths = pytest_config.get("testpaths", ["tests"])
        # Use first test path for cache validation
        test_path = testpaths[0] if testpaths else "tests"

        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]

        # Add fail-fast if configured (useful for cache validation)
        if pytest_config.get("fail_fast", False):
            cmd.append("-x")

        return cmd

    def _measure_baseline(self, repo_path: Path) -> float | None:
        """Measure test suite time without caching.

        Returns:
            Average time in seconds, or None if tests failed
        """
        times = []
        cmd = self._build_pytest_command()

        for _ in range(self.num_runs):
            start = time.perf_counter()

            try:
                result = subprocess.run(
                    cmd,
                    check=False,
                    cwd=repo_path,
                    capture_output=True,
                    timeout=self.test_timeout,
                )

                if result.returncode != 0:
                    return None

                elapsed = time.perf_counter() - start
                times.append(elapsed)

            except (subprocess.TimeoutExpired, Exception):
                return None

        # Return average
        return sum(times) / len(times)

    def _measure_with_cache(
        self,
        candidate,
        repo_path: Path,
        patcher: "SourcePatcher",
    ) -> tuple[float | None, object | None]:
        """Measure test suite time WITH caching.

        Uses in-memory file backup/restore for safe modification.

        Args:
            candidate: Candidate to test
            repo_path: Repository path
            patcher: SourcePatcher instance (already on cache branch)

        Returns:
            (average_time, cache_info) or (None, None) if failed
        """
        # Backup file before modifying
        if not patcher.backup_file(candidate.file_path):
            return (None, None)

        try:
            # Apply cache decorator to source file
            success = patcher.apply_cache_decorator(
                file_path=candidate.file_path,
                function_name=candidate.function_name,
                cache_size=self.cache_size,
            )

            if not success:
                return (None, None)

            # Run tests multiple times
            times = []
            cmd = self._build_pytest_command()

            for _ in range(self.num_runs):
                start = time.perf_counter()

                try:
                    result = subprocess.run(
                        cmd,
                        check=False,
                        cwd=repo_path,
                        capture_output=True,
                        timeout=self.test_timeout,
                    )

                    if result.returncode != 0:
                        # Tests failed - restore and return
                        patcher.restore_file(candidate.file_path)
                        return (None, None)

                    elapsed = time.perf_counter() - start
                    times.append(elapsed)

                except (subprocess.TimeoutExpired, Exception):
                    # Timeout or error - restore and return
                    patcher.restore_file(candidate.file_path)
                    return (None, None)

            # Import modified module to get cache statistics
            module = importlib.import_module(candidate.module_path)
            importlib.reload(module)
            cached_func = getattr(module, candidate.function_name)
            cache_info = cached_func.cache_info()

            # Restore original file (for next candidate test)
            patcher.restore_file(candidate.file_path)

            avg_time = sum(times) / len(times)
            return (avg_time, cache_info)

        except Exception:
            # Always restore on error
            patcher.restore_file(candidate.file_path)
            return (None, None)

    def _calculate_speedup(self, baseline: float, cached: float) -> float:
        """Calculate speedup percentage."""
        if baseline == 0:
            return 0.0
        improvement = ((baseline - cached) / baseline) * 100.0
        return max(improvement, 0.0)  # Don't report negative speedup

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0

    def _make_recommendation(
        self,
        speedup: float,
        hit_rate: float,
    ) -> tuple[str, str | None]:
        """Determine recommendation based on metrics.

        Returns:
            (recommendation, rejection_reason)
        """
        # Both criteria must pass
        if hit_rate < 20.0:
            return ("REJECT", f"Hit rate too low: {hit_rate:.1f}% < 20%")

        if speedup < self.speedup_threshold:
            return ("REJECT", f"Speedup too low: {speedup:.1f}% < {self.speedup_threshold}%")

        return ("APPLY", None)
