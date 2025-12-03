"""Hotspot analysis from profiling data.

Identifies functions called frequently with significant execution time.
"""

import pstats
from pathlib import Path

from glintefy.subservers.review.cache.cache_models import CacheCandidate, Hotspot, PureFunctionCandidate


class HotspotAnalyzer:
    """Analyze profiling data to find performance hotspots."""

    # Default root markers for module path inference
    DEFAULT_ROOT_MARKERS = ("src", "lib")

    def __init__(
        self,
        min_calls: int = 100,
        min_cumtime: float = 0.1,
        root_markers: tuple[str, ...] | None = None,
        high_priority_calls: int = 500,
        high_priority_time: float = 1.0,
        high_priority_indicators: int = 2,
        medium_priority_calls: int = 200,
        medium_priority_time: float = 0.5,
    ):
        """Initialize hotspot analyzer.

        Args:
            min_calls: Minimum number of calls to be considered a hotspot
            min_cumtime: Minimum cumulative time (seconds) to be a hotspot
            root_markers: Directory names that mark module roots (e.g., "src", "lib")
            high_priority_calls: Call count threshold for HIGH priority
            high_priority_time: Cumulative time threshold for HIGH priority
            high_priority_indicators: Indicator count threshold for HIGH priority
            medium_priority_calls: Call count threshold for MEDIUM priority
            medium_priority_time: Cumulative time threshold for MEDIUM priority
        """
        self.min_calls = min_calls
        self.min_cumtime = min_cumtime
        self.root_markers = root_markers or self.DEFAULT_ROOT_MARKERS
        self.high_priority_calls = high_priority_calls
        self.high_priority_time = high_priority_time
        self.high_priority_indicators = high_priority_indicators
        self.medium_priority_calls = medium_priority_calls
        self.medium_priority_time = medium_priority_time

    def analyze_profile(self, prof_file: Path) -> list[Hotspot]:
        """Extract hotspots from cProfile output.

        Args:
            prof_file: Path to .prof file from cProfile

        Returns:
            List of hotspots sorted by cumulative time
        """
        if not prof_file.exists():
            return []

        try:
            stats = pstats.Stats(str(prof_file))
        except Exception:
            return []

        hotspots = []

        for func, (_cc, nc, _tt, ct, _callers) in stats.stats.items():
            # Filter by thresholds
            if nc < self.min_calls or ct < self.min_cumtime:
                continue

            # Extract file path, line, function name
            filename, line, func_name = func

            # Skip built-ins and libraries
            if "<" in filename or "site-packages" in filename:
                continue

            # Skip standard library
            if "/lib/python" in filename or "/lib64/python" in filename:
                continue

            hotspots.append(
                Hotspot(
                    file_path=Path(filename),
                    function_name=func_name,
                    line_number=line,
                    call_count=nc,
                    cumulative_time=ct,
                    time_per_call=ct / nc if nc > 0 else 0,
                )
            )

        # Sort by cumulative time (highest first)
        hotspots.sort(key=lambda h: h.cumulative_time, reverse=True)

        return hotspots

    def cross_reference(
        self,
        pure_candidates: list[PureFunctionCandidate],
        hotspots: list[Hotspot],
    ) -> list[CacheCandidate]:
        """Cross-reference pure functions with hotspots.

        Returns candidates that are BOTH pure AND frequently called.

        Args:
            pure_candidates: Pure functions from AST analysis
            hotspots: Hot functions from profiling

        Returns:
            High-priority cache candidates
        """
        # Filter to only pure functions
        pure_funcs = [c for c in pure_candidates if c.is_pure]

        candidates = []

        for pure_func in pure_funcs:
            for hotspot in hotspots:
                # Match by function name and file
                if self._matches(pure_func, hotspot):
                    # Calculate module path for import
                    module_path = self._infer_module_path(pure_func.file_path)

                    # Determine priority based on metrics
                    priority = self._calculate_priority(hotspot.call_count, hotspot.cumulative_time, pure_func.expense_indicators)

                    candidates.append(
                        CacheCandidate(
                            file_path=pure_func.file_path,
                            function_name=pure_func.function_name,
                            line_number=pure_func.line_number,
                            module_path=module_path,
                            call_count=hotspot.call_count,
                            cumulative_time=hotspot.cumulative_time,
                            expense_indicators=pure_func.expense_indicators,
                            priority=priority,
                        )
                    )
                    break

        # Sort by priority and cumulative time
        candidates.sort(key=lambda c: (c.priority == "HIGH", c.cumulative_time), reverse=True)

        return candidates

    def _matches(
        self,
        pure_func: PureFunctionCandidate,
        hotspot: Hotspot,
    ) -> bool:
        """Check if pure function matches hotspot."""
        # Function name must match
        if pure_func.function_name != hotspot.function_name:
            return False

        # File should match (compare absolute paths or basenames)
        try:
            # Try absolute path comparison first
            if pure_func.file_path.resolve() == hotspot.file_path.resolve():
                return True
        except Exception:
            pass

        # Fallback to basename comparison
        pure_file = pure_func.file_path.name
        hot_file = hotspot.file_path.name

        return pure_file == hot_file

    def _infer_module_path(self, file_path: Path) -> str:
        """Infer Python module path from file path.

        Example: src/glintefy/config.py -> glintefy.config
        """
        parts = file_path.parts

        for i, part in enumerate(parts):
            if part not in self.root_markers:
                continue

            # "src" and "lib" are container dirs - module starts after them
            # Other markers (like package names) are included in the module path
            if part in ("src", "lib"):
                module_parts = list(parts[i + 1 :])
            else:
                module_parts = list(parts[i:])

            return self._normalize_module_parts(module_parts)

        # Fallback: use relative path without extension
        return str(file_path.with_suffix("")).replace("/", ".")

    def _normalize_module_parts(self, module_parts: list[str]) -> str:
        """Normalize module path parts to dotted module name.

        Args:
            module_parts: List of path components

        Returns:
            Dotted module path string
        """
        if not module_parts:
            return ""

        # Remove .py extension from last part
        module_parts[-1] = module_parts[-1].removesuffix(".py")

        # Remove __init__ if present
        if module_parts and module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]

        return ".".join(module_parts)

    def _calculate_priority(
        self,
        call_count: int,
        cumtime: float,
        indicators: list[str],
    ) -> str:
        """Calculate priority based on metrics and configured thresholds."""
        # High priority: many calls + significant time + expensive ops
        high_calls_met = call_count >= self.high_priority_calls
        high_time_met = cumtime >= self.high_priority_time
        high_indicators_met = len(indicators) >= self.high_priority_indicators
        if high_calls_met and high_time_met and high_indicators_met:
            return "HIGH"

        # Medium priority: decent calls or time
        medium_calls_met = call_count >= self.medium_priority_calls
        medium_time_met = cumtime >= self.medium_priority_time
        if medium_calls_met or medium_time_met:
            return "MEDIUM"

        return "LOW"
