# Cache Analysis Sub-Server Implementation Plan

**Date:** 2025-11-23
**Status:** Planning Phase
**Target:** Add cache optimization analysis to glintefy review system

---

## 🎯 Overview

Implement a cache analysis sub-server that identifies caching opportunities using a hybrid approach:
1. **Batch Screening** - Fast filtering of candidates by cache hit rate
2. **Individual Validation** - Precise measurement of performance impact

---

## 📋 Implementation Tasks

### Phase 1: Core Architecture & Data Structures

#### Task 1.1: Create Base Module Structure

**Files to create:**
```
src/glintefy/subservers/review/cache/
├── __init__.py
├── cache_analyzer.py          # Main CacheSubServer class
├── pure_function_detector.py  # Stage 1: AST-based purity detection
├── hotspot_analyzer.py         # Stage 2: Profiling cross-reference
├── batch_screener.py           # Stage 3A: Batch cache testing
├── individual_validator.py     # Stage 3B: Individual cache testing
└── cache_models.py             # Data classes for cache analysis
```

**Data Structures:**

```python
# cache_models.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PureFunctionCandidate:
    """Result from AST analysis - potentially cacheable function."""
    file_path: Path
    function_name: str
    line_number: int
    is_pure: bool
    expense_indicators: list[str]  # ['loops', 'recursion', 'crypto']
    disqualifiers: list[str]       # Reasons if not pure

@dataclass
class Hotspot:
    """Function called frequently with significant time cost."""
    file_path: Path
    function_name: str
    line_number: int
    call_count: int
    cumulative_time: float
    time_per_call: float

@dataclass
class CacheCandidate:
    """High-priority candidate - both pure AND hot."""
    file_path: Path
    function_name: str
    line_number: int
    module_path: str              # For import (e.g., "glintefy.config")
    call_count: int
    cumulative_time: float
    expense_indicators: list[str]
    priority: str                 # "HIGH", "MEDIUM", "LOW"

@dataclass
class BatchScreeningResult:
    """Results from batch cache testing."""
    candidate: CacheCandidate
    hits: int
    misses: int
    hit_rate: float              # Percentage
    maxsize: int
    currsize: int
    passed_screening: bool        # hit_rate >= threshold

@dataclass
class IndividualValidationResult:
    """Results from individual cache testing."""
    candidate: CacheCandidate
    baseline_time: float          # Test suite time without cache (seconds)
    cached_time: float            # Test suite time with cache (seconds)
    speedup_percent: float        # Percentage improvement
    hits: int
    misses: int
    hit_rate: float
    recommendation: str           # "APPLY", "REJECT"
    rejection_reason: str | None  # If rejected

@dataclass
class CacheRecommendation:
    """Final recommendation for production deployment."""
    file_path: Path
    function_name: str
    line_number: int
    module_path: str
    decorator: str                # "@lru_cache(maxsize=128)"
    expected_speedup: float       # Percentage
    cache_hit_rate: float         # Percentage
    evidence: dict                # All measurements
```

---

### Phase 2: Stage 1 - Pure Function Detection

#### Task 2.1: Implement AST-Based Purity Analyzer

**File:** `src/glintefy/subservers/review/cache/pure_function_detector.py`

```python
"""AST-based pure function detection.

Identifies functions that are deterministic and side-effect free,
making them candidates for caching.
"""

import ast
from pathlib import Path
from typing import List

from glintefy.subservers.review.cache.cache_models import PureFunctionCandidate


class PureFunctionDetector:
    """Detect pure functions using AST analysis."""

    # Disqualifying patterns
    IO_OPERATIONS = ['print', 'open', 'input', 'write', 'read', 'execute']
    NON_DETERMINISTIC = ['now', 'today', 'random', 'randint', 'uuid']

    def analyze_file(self, file_path: Path) -> List[PureFunctionCandidate]:
        """Analyze a single Python file for pure functions.

        Args:
            file_path: Path to Python file

        Returns:
            List of pure function candidates
        """
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            return []

        candidates = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip if already has cache decorator
                if self._has_cache_decorator(node):
                    continue

                # Analyze purity
                is_pure, disqualifiers = self._is_pure_function(node)

                if is_pure:
                    # Analyze expense indicators
                    indicators = self._detect_expense_indicators(node)

                    candidates.append(PureFunctionCandidate(
                        file_path=file_path,
                        function_name=node.name,
                        line_number=node.lineno,
                        is_pure=True,
                        expense_indicators=indicators,
                        disqualifiers=[]
                    ))
                else:
                    # Record why it's not pure (for debugging)
                    candidates.append(PureFunctionCandidate(
                        file_path=file_path,
                        function_name=node.name,
                        line_number=node.lineno,
                        is_pure=False,
                        expense_indicators=[],
                        disqualifiers=disqualifiers
                    ))

        return candidates

    def _has_cache_decorator(self, func_node: ast.FunctionDef) -> bool:
        """Check if function already has a cache decorator."""
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Name) and 'cache' in decorator.id.lower():
                return True
            if isinstance(decorator, ast.Call):
                if hasattr(decorator.func, 'id') and 'cache' in decorator.func.id.lower():
                    return True
        return False

    def _is_pure_function(self, func_node: ast.FunctionDef) -> tuple[bool, list[str]]:
        """Check if function is pure (deterministic, no side effects).

        Returns:
            (is_pure, disqualifiers)
        """
        disqualifiers = []

        for node in ast.walk(func_node):
            # Check for I/O operations
            if isinstance(node, ast.Call):
                if self._is_io_call(node):
                    disqualifiers.append("I/O operation")
                if self._is_non_deterministic_call(node):
                    disqualifiers.append("Non-deterministic (time/random)")

            # Check for global/nonlocal state modification
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                disqualifiers.append("Global/nonlocal state")

            # Check for attribute assignment (potential side effects)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                disqualifiers.append("Attribute modification")

        return (len(disqualifiers) == 0, disqualifiers)

    def _is_io_call(self, node: ast.Call) -> bool:
        """Check if call is I/O operation."""
        if isinstance(node.func, ast.Name):
            return node.func.id in self.IO_OPERATIONS
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in self.IO_OPERATIONS
        return False

    def _is_non_deterministic_call(self, node: ast.Call) -> bool:
        """Check if call is non-deterministic (time, random, etc.)."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in self.NON_DETERMINISTIC
        return False

    def _detect_expense_indicators(self, func_node: ast.FunctionDef) -> list[str]:
        """Detect patterns indicating computational expense."""
        indicators = []

        # Nested loops
        if self._has_nested_loops(func_node):
            indicators.append('nested_loops')

        # Recursion
        if self._is_recursive(func_node):
            indicators.append('recursion')

        # Crypto/hash operations
        if self._has_crypto_operations(func_node):
            indicators.append('crypto')

        # File operations (even if pure - e.g., read-only)
        if self._has_file_operations(func_node):
            indicators.append('file_io')

        return indicators

    def _has_nested_loops(self, func_node: ast.FunctionDef, depth: int = 2) -> bool:
        """Check for nested loops (depth >= 2)."""
        def count_nesting(node, current_depth=0):
            max_depth = current_depth
            for child in ast.walk(node):
                if isinstance(child, (ast.For, ast.While)):
                    child_depth = count_nesting(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
            return max_depth

        return count_nesting(func_node) >= depth

    def _is_recursive(self, func_node: ast.FunctionDef) -> bool:
        """Check if function calls itself."""
        func_name = func_node.name
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    return True
        return False

    def _has_crypto_operations(self, func_node: ast.FunctionDef) -> bool:
        """Check for cryptographic/hash operations."""
        crypto_keywords = ['hash', 'crypt', 'encrypt', 'decrypt', 'sha', 'md5']
        code = ast.unparse(func_node).lower()
        return any(kw in code for kw in crypto_keywords)

    def _has_file_operations(self, func_node: ast.FunctionDef) -> bool:
        """Check for file operations (even read-only)."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'open':
                    return True
        return False
```

**Tests:** `tests/subservers/review/cache/test_pure_function_detector.py`

```python
def test_detects_pure_function():
    code = '''
def calculate_hash(data: str) -> str:
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()
'''
    # Should detect as pure with 'crypto' indicator

def test_rejects_io_function():
    code = '''
def log_message(msg: str) -> None:
    with open('log.txt', 'a') as f:
        f.write(msg)
'''
    # Should reject: I/O operation

def test_rejects_non_deterministic():
    code = '''
def get_timestamp() -> float:
    import time
    return time.time()
'''
    # Should reject: Non-deterministic

def test_detects_nested_loops():
    code = '''
def matrix_multiply(a, b):
    result = []
    for i in range(len(a)):
        row = []
        for j in range(len(b[0])):
            row.append(sum(a[i][k] * b[k][j] for k in range(len(b))))
        result.append(row)
    return result
'''
    # Should detect 'nested_loops' indicator
```

---

### Phase 3: Stage 2 - Hotspot Analysis

#### Task 3.1: Implement Profiling Data Cross-Reference

**File:** `src/glintefy/subservers/review/cache/hotspot_analyzer.py`

```python
"""Hotspot analysis from profiling data.

Identifies functions called frequently with significant execution time.
"""

import pstats
from pathlib import Path
from typing import List

from glintefy.subservers.review.cache.cache_models import (
    CacheCandidate,
    Hotspot,
    PureFunctionCandidate,
)


class HotspotAnalyzer:
    """Analyze profiling data to find performance hotspots."""

    def __init__(
        self,
        min_calls: int = 100,
        min_cumtime: float = 0.1,
    ):
        """Initialize hotspot analyzer.

        Args:
            min_calls: Minimum number of calls to be considered
            min_cumtime: Minimum cumulative time (seconds)
        """
        self.min_calls = min_calls
        self.min_cumtime = min_cumtime

    def analyze_profile(self, prof_file: Path) -> List[Hotspot]:
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

        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            # Filter by thresholds
            if nc < self.min_calls or ct < self.min_cumtime:
                continue

            # Extract file path, line, function name
            filename, line, func_name = func

            # Skip built-ins and libraries
            if '<' in filename or 'site-packages' in filename:
                continue

            hotspots.append(Hotspot(
                file_path=Path(filename),
                function_name=func_name,
                line_number=line,
                call_count=nc,
                cumulative_time=ct,
                time_per_call=ct / nc if nc > 0 else 0,
            ))

        # Sort by cumulative time (highest first)
        hotspots.sort(key=lambda h: h.cumulative_time, reverse=True)

        return hotspots

    def cross_reference(
        self,
        pure_candidates: List[PureFunctionCandidate],
        hotspots: List[Hotspot],
    ) -> List[CacheCandidate]:
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
                    priority = self._calculate_priority(
                        hotspot.call_count,
                        hotspot.cumulative_time,
                        pure_func.expense_indicators
                    )

                    candidates.append(CacheCandidate(
                        file_path=pure_func.file_path,
                        function_name=pure_func.function_name,
                        line_number=pure_func.line_number,
                        module_path=module_path,
                        call_count=hotspot.call_count,
                        cumulative_time=hotspot.cumulative_time,
                        expense_indicators=pure_func.expense_indicators,
                        priority=priority,
                    ))
                    break

        # Sort by priority and cumulative time
        candidates.sort(key=lambda c: (
            c.priority == "HIGH",
            c.cumulative_time
        ), reverse=True)

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

        # File should match (compare basenames to handle path differences)
        pure_file = pure_func.file_path.name
        hot_file = hotspot.file_path.name

        return pure_file == hot_file

    def _infer_module_path(self, file_path: Path) -> str:
        """Infer Python module path from file path.

        Example: src/glintefy/config.py → glintefy.config
        """
        # Try to find src/ or package root
        parts = file_path.parts

        # Look for common root directories
        root_markers = ['src', 'lib', 'glintefy']

        for i, part in enumerate(parts):
            if part in root_markers:
                # Module path starts after root
                module_parts = parts[i+1:] if part == 'src' else parts[i:]

                # Remove .py extension
                module_parts = list(module_parts)
                if module_parts[-1].endswith('.py'):
                    module_parts[-1] = module_parts[-1][:-3]

                return '.'.join(module_parts)

        # Fallback: use relative path
        return str(file_path.with_suffix('')).replace('/', '.')

    def _calculate_priority(
        self,
        call_count: int,
        cumtime: float,
        indicators: list[str],
    ) -> str:
        """Calculate priority based on metrics."""
        # High priority: many calls + significant time + expensive ops
        if call_count >= 500 and cumtime >= 1.0 and len(indicators) >= 2:
            return "HIGH"

        # Medium priority: decent calls or time
        if call_count >= 200 or cumtime >= 0.5:
            return "MEDIUM"

        return "LOW"
```

---

### Phase 4: Stage 3A - Batch Screening

#### Task 4.1: Implement Batch Cache Testing

**File:** `src/glintefy/subservers/review/cache/batch_screener.py`

```python
"""Batch cache screening.

Tests all candidates simultaneously to filter by cache hit rate.
This is the FAST phase that eliminates obvious losers.
"""

import importlib
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import List

from glintefy.subservers.review.cache.cache_models import (
    BatchScreeningResult,
    CacheCandidate,
)


class BatchScreener:
    """Screen cache candidates in batch for hit rate."""

    def __init__(
        self,
        cache_size: int = 128,
        hit_rate_threshold: float = 20.0,
        test_timeout: int = 300,
    ):
        """Initialize batch screener.

        Args:
            cache_size: LRU cache maxsize
            hit_rate_threshold: Minimum hit rate percentage to pass
            test_timeout: Test suite timeout in seconds
        """
        self.cache_size = cache_size
        self.hit_rate_threshold = hit_rate_threshold
        self.test_timeout = test_timeout
        self._cached_funcs = []

    def screen_candidates(
        self,
        candidates: List[CacheCandidate],
        repo_path: Path,
    ) -> List[BatchScreeningResult]:
        """Screen all candidates in a single test run.

        Args:
            candidates: Cache candidates to test
            repo_path: Repository root path

        Returns:
            Screening results for each candidate
        """
        if not candidates:
            return []

        # Apply caches to ALL candidates
        self._apply_caches(candidates)

        # Run test suite ONCE
        test_passed = self._run_test_suite(repo_path)

        # Collect cache statistics
        results = []
        for candidate, cached_func in zip(candidates, self._cached_funcs):
            cache_info = cached_func.cache_info()

            hit_rate = self._calculate_hit_rate(
                cache_info.hits,
                cache_info.misses
            )

            passed = hit_rate >= self.hit_rate_threshold

            results.append(BatchScreeningResult(
                candidate=candidate,
                hits=cache_info.hits,
                misses=cache_info.misses,
                hit_rate=hit_rate,
                maxsize=cache_info.maxsize,
                currsize=cache_info.currsize,
                passed_screening=passed,
            ))

        # Restore original functions
        self._restore_originals(candidates)

        return results

    def _apply_caches(self, candidates: List[CacheCandidate]) -> None:
        """Apply LRU cache to all candidate functions."""
        self._cached_funcs = []

        for candidate in candidates:
            try:
                # Import module
                module = importlib.import_module(candidate.module_path)

                # Get original function
                original_func = getattr(module, candidate.function_name)

                # Apply cache
                cached_func = lru_cache(maxsize=self.cache_size)(original_func)

                # Monkey-patch module
                setattr(module, candidate.function_name, cached_func)

                # Store for statistics collection
                self._cached_funcs.append(cached_func)

            except Exception:
                # If import/patch fails, use dummy
                self._cached_funcs.append(None)

    def _run_test_suite(self, repo_path: Path) -> bool:
        """Run pytest test suite.

        Returns:
            True if tests passed
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 'tests/', '-v'],
                cwd=repo_path,
                capture_output=True,
                timeout=self.test_timeout,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0

    def _restore_originals(self, candidates: List[CacheCandidate]) -> None:
        """Restore original functions (remove caches)."""
        # Note: In practice, we can't easily restore without tracking originals
        # This is acceptable since screening is exploratory
        # For production, we'd need to track originals in _apply_caches
        pass
```

---

### Phase 5: Stage 3B - Individual Validation

#### Task 5.1: Implement Individual Cache Testing

**File:** `src/glintefy/subservers/review/cache/individual_validator.py`

```python
"""Individual cache validation.

Tests each surviving candidate individually to measure precise impact.
This is the SLOW phase that provides accurate measurements.
"""

import importlib
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import List

from glintefy.subservers.review.cache.cache_models import (
    BatchScreeningResult,
    IndividualValidationResult,
)


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
        screening_results: List[BatchScreeningResult],
        repo_path: Path,
    ) -> List[IndividualValidationResult]:
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

        for screening_result in survivors:
            candidate = screening_result.candidate

            # Measure baseline (without cache)
            baseline_time = self._measure_baseline(repo_path)

            if baseline_time is None:
                # Test suite failed - skip this candidate
                continue

            # Measure with cache
            cached_time, cache_info = self._measure_with_cache(
                candidate,
                repo_path
            )

            if cached_time is None:
                # Test suite failed - skip this candidate
                continue

            # Calculate metrics
            speedup = self._calculate_speedup(baseline_time, cached_time)
            hit_rate = self._calculate_hit_rate(
                cache_info.hits,
                cache_info.misses
            )

            # Determine recommendation
            recommendation, reason = self._make_recommendation(
                speedup,
                hit_rate
            )

            results.append(IndividualValidationResult(
                candidate=candidate,
                baseline_time=baseline_time,
                cached_time=cached_time,
                speedup_percent=speedup,
                hits=cache_info.hits,
                misses=cache_info.misses,
                hit_rate=hit_rate,
                recommendation=recommendation,
                rejection_reason=reason,
            ))

        return results

    def _measure_baseline(self, repo_path: Path) -> float | None:
        """Measure test suite time without caching.

        Returns:
            Average time in seconds, or None if tests failed
        """
        times = []

        for _ in range(self.num_runs):
            start = time.perf_counter()

            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pytest', 'tests/', '-v'],
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
    ) -> tuple[float | None, object]:
        """Measure test suite time WITH caching.

        Returns:
            (average_time, cache_info) or (None, None) if failed
        """
        try:
            # Import and patch
            module = importlib.import_module(candidate.module_path)
            original_func = getattr(module, candidate.function_name)
            cached_func = lru_cache(maxsize=self.cache_size)(original_func)
            setattr(module, candidate.function_name, cached_func)

            times = []

            for _ in range(self.num_runs):
                start = time.perf_counter()

                try:
                    result = subprocess.run(
                        [sys.executable, '-m', 'pytest', 'tests/', '-v'],
                        cwd=repo_path,
                        capture_output=True,
                        timeout=self.test_timeout,
                    )

                    if result.returncode != 0:
                        return (None, None)

                    elapsed = time.perf_counter() - start
                    times.append(elapsed)

                except (subprocess.TimeoutExpired, Exception):
                    return (None, None)

            # Get cache statistics
            cache_info = cached_func.cache_info()

            # Restore original
            setattr(module, candidate.function_name, original_func)

            avg_time = sum(times) / len(times)
            return (avg_time, cache_info)

        except Exception:
            return (None, None)

    def _calculate_speedup(self, baseline: float, cached: float) -> float:
        """Calculate speedup percentage."""
        if baseline == 0:
            return 0.0
        return ((baseline - cached) / baseline) * 100.0

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
```

---

### Phase 6: Main Cache Sub-Server

#### Task 6.1: Implement CacheSubServer

**File:** `src/glintefy/subservers/review/cache.py`

```python
"""Cache Analysis Sub-Server.

Identifies caching opportunities using hybrid approach:
1. AST analysis - identify pure functions
2. Profiling cross-reference - find hot spots
3. Batch screening - filter by hit rate
4. Individual validation - measure precise impact
"""

from pathlib import Path

from glintefy.config import get_config
from glintefy.subservers.common.base import BaseSubServer, SubServerResult
from glintefy.subservers.common.logging import get_mcp_logger, log_debug
from glintefy.subservers.review.cache.batch_screener import BatchScreener
from glintefy.subservers.review.cache.hotspot_analyzer import HotspotAnalyzer
from glintefy.subservers.review.cache.individual_validator import IndividualValidator
from glintefy.subservers.review.cache.pure_function_detector import PureFunctionDetector


class CacheSubServer(BaseSubServer):
    """Cache analysis sub-server."""

    name = "cache"

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
            mcp_mode: Enable MCP logging mode
        """
        super().__init__(output_dir, repo_path, mcp_mode)

        self.input_dir = input_dir

        # Load config
        config = get_config(start_dir=str(repo_path))
        cache_config = config.get("review", {}).get("cache", {})

        # Apply config with constructor overrides
        self.cache_size = cache_size or cache_config.get("cache_size", 128)
        self.hit_rate_threshold = hit_rate_threshold or cache_config.get("hit_rate_threshold", 20.0)
        self.speedup_threshold = speedup_threshold or cache_config.get("speedup_threshold", 5.0)
        self.min_calls = min_calls or cache_config.get("min_calls", 100)
        self.min_cumtime = min_cumtime or cache_config.get("min_cumtime", 0.1)

        # Initialize analyzers
        self.pure_detector = PureFunctionDetector()
        self.hotspot_analyzer = HotspotAnalyzer(
            min_calls=self.min_calls,
            min_cumtime=self.min_cumtime,
        )
        self.batch_screener = BatchScreener(
            cache_size=self.cache_size,
            hit_rate_threshold=self.hit_rate_threshold,
        )
        self.individual_validator = IndividualValidator(
            cache_size=self.cache_size,
            speedup_threshold=self.speedup_threshold,
        )

    def run(self) -> SubServerResult:
        """Run cache analysis pipeline."""
        log_debug(self._logger, "Starting cache analysis")

        try:
            # Stage 1: Identify pure functions
            pure_candidates = self._identify_pure_functions()
            log_debug(self._logger, f"Found {len(pure_candidates)} pure function candidates")

            # Stage 2: Cross-reference with profiling data
            cache_candidates = self._cross_reference_hotspots(pure_candidates)
            log_debug(self._logger, f"Found {len(cache_candidates)} cache candidates (pure + hot)")

            if not cache_candidates:
                return self._create_empty_result()

            # Stage 3A: Batch screening
            screening_results = self._batch_screen(cache_candidates)
            survivors = [r for r in screening_results if r.passed_screening]
            log_debug(self._logger, f"Batch screening: {len(survivors)}/{len(cache_candidates)} passed")

            if not survivors:
                return self._create_screening_result(screening_results)

            # Stage 3B: Individual validation
            validation_results = self._individual_validate(screening_results)
            recommendations = [r for r in validation_results if r.recommendation == "APPLY"]
            log_debug(self._logger, f"Individual validation: {len(recommendations)} recommended")

            # Generate outputs
            return self._create_final_result(
                pure_candidates,
                cache_candidates,
                screening_results,
                validation_results,
            )

        except Exception as e:
            self._logger.error(f"Cache analysis failed: {e}", exc_info=True)
            return SubServerResult(
                status="FAILED",
                summary=f"Cache analysis failed: {e}",
                metrics={},
                artifacts={},
                errors=[str(e)],
            )

    def _identify_pure_functions(self) -> list:
        """Stage 1: AST-based pure function detection."""
        # Read files from scope
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []

        python_files = []
        for line in files_list.read_text().splitlines():
            path = Path(line.strip())
            if path.suffix == '.py':
                python_files.append(path)

        # Analyze each file
        all_candidates = []
        for file_path in python_files:
            candidates = self.pure_detector.analyze_file(file_path)
            all_candidates.extend(candidates)

        return all_candidates

    def _cross_reference_hotspots(self, pure_candidates: list) -> list:
        """Stage 2: Cross-reference with profiling data."""
        # Look for profiling data from perf sub-server
        prof_file = self.input_dir.parent / "perf" / "test_profile.prof"

        if not prof_file.exists():
            # No profiling data - return empty
            return []

        hotspots = self.hotspot_analyzer.analyze_profile(prof_file)
        cache_candidates = self.hotspot_analyzer.cross_reference(
            pure_candidates,
            hotspots,
        )

        return cache_candidates

    def _batch_screen(self, candidates: list) -> list:
        """Stage 3A: Batch screening."""
        return self.batch_screener.screen_candidates(
            candidates,
            self.repo_path,
        )

    def _individual_validate(self, screening_results: list) -> list:
        """Stage 3B: Individual validation."""
        return self.individual_validator.validate_candidates(
            screening_results,
            self.repo_path,
        )

    def _create_empty_result(self) -> SubServerResult:
        """Create result when no candidates found."""
        summary = "# Cache Analysis\n\nNo cacheable functions found."

        return SubServerResult(
            status="SUCCESS",
            summary=summary,
            metrics={
                "pure_functions": 0,
                "cache_candidates": 0,
                "batch_passed": 0,
                "recommendations": 0,
            },
            artifacts={},
            errors=[],
        )

    def _create_screening_result(self, screening_results: list) -> SubServerResult:
        """Create result when screening filtered all candidates."""
        summary = f"# Cache Analysis\n\n{len(screening_results)} candidates screened, none passed hit rate threshold."

        return SubServerResult(
            status="SUCCESS",
            summary=summary,
            metrics={
                "cache_candidates": len(screening_results),
                "batch_passed": 0,
                "recommendations": 0,
            },
            artifacts={},
            errors=[],
        )

    def _create_final_result(
        self,
        pure_candidates: list,
        cache_candidates: list,
        screening_results: list,
        validation_results: list,
    ) -> SubServerResult:
        """Create final result with all data."""
        recommendations = [r for r in validation_results if r.recommendation == "APPLY"]

        # Generate summary
        summary = self._generate_summary(
            pure_candidates,
            cache_candidates,
            screening_results,
            validation_results,
        )

        # Save artifacts
        artifacts = self._save_artifacts(
            pure_candidates,
            cache_candidates,
            screening_results,
            validation_results,
        )

        status = "SUCCESS" if len(recommendations) > 0 else "PARTIAL"

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
            },
            artifacts=artifacts,
            errors=[],
        )

    def _generate_summary(self, pure, candidates, screening, validation) -> str:
        """Generate markdown summary."""
        recommendations = [r for r in validation if r.recommendation == "APPLY"]

        lines = [
            "# Cache Analysis Report",
            "",
            "## Overview",
            "",
            f"- Pure functions identified: {len([c for c in pure if c.is_pure])}",
            f"- Cache candidates (pure + hot): {len(candidates)}",
            f"- Batch screening passed: {len([r for r in screening if r.passed_screening])}/{len(screening)}",
            f"- Individual validation: {len(validation)} tested",
            f"- **Recommendations: {len(recommendations)}**",
            "",
        ]

        if recommendations:
            lines.extend([
                "## Recommended Caching",
                "",
            ])

            for result in recommendations:
                c = result.candidate
                lines.extend([
                    f"### {c.function_name} ({c.file_path.name}:{c.line_number})",
                    f"- **Expected speedup:** {result.speedup_percent:.1f}%",
                    f"- **Cache hit rate:** {result.hit_rate:.1f}%",
                    f"- **Decorator:** `@lru_cache(maxsize={self.cache_size})`",
                    "",
                ])

        return "\n".join(lines)

    def _save_artifacts(self, pure, candidates, screening, validation) -> dict:
        """Save all artifacts to output directory."""
        import json

        artifacts = {}

        # Save recommendations as JSON
        recommendations = [r for r in validation if r.recommendation == "APPLY"]
        if recommendations:
            recs_file = self.output_dir / "cache_recommendations.json"
            recs_data = [
                {
                    "file": str(r.candidate.file_path),
                    "function": r.candidate.function_name,
                    "line": r.candidate.line_number,
                    "module": r.candidate.module_path,
                    "decorator": f"@lru_cache(maxsize={self.cache_size})",
                    "speedup_percent": r.speedup_percent,
                    "hit_rate_percent": r.hit_rate,
                }
                for r in recommendations
            ]
            recs_file.write_text(json.dumps(recs_data, indent=2))
            artifacts["recommendations"] = recs_file

        return artifacts
```

---

### Phase 7: Integration with Review System

#### Task 7.1: Add to ReviewMCPServer

**File:** `src/glintefy/servers/review.py` (modify)

```python
# Add import
from glintefy.subservers.review.cache import CacheSubServer

# Add method to ReviewMCPServer class
@debug_log(logger)
def run_cache(
    self,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    cache_size: int | None = None,
    hit_rate_threshold: float | None = None,
    speedup_threshold: float | None = None,
) -> dict[str, Any]:
    """Run cache analysis.

    Args:
        input_dir: Input directory with scope + perf results
        output_dir: Output directory (default: LLM-CONTEXT/glintefy/review/cache)
        cache_size: Override cache size
        hit_rate_threshold: Override hit rate threshold
        speedup_threshold: Override speedup threshold

    Returns:
        Dictionary with status, summary, metrics, and artifact paths
    """
    input_path = input_dir or self._output_base / "scope"
    output_path = output_dir or self._output_base / "cache"

    server = CacheSubServer(
        input_dir=input_path,
        output_dir=output_path,
        repo_path=self.repo_path,
        cache_size=cache_size,
        hit_rate_threshold=hit_rate_threshold,
        speedup_threshold=speedup_threshold,
        mcp_mode=True,
    )

    import time
    start = time.perf_counter()
    result = server.run()
    duration_ms = (time.perf_counter() - start) * 1000

    log_tool_execution(
        logger, "cache",
        result.metrics.get("cache_candidates", 0),
        result.status,
        result.metrics.get("recommendations", 0),
        duration_ms
    )

    return {
        "status": result.status,
        "summary": result.summary,
        "metrics": result.metrics,
        "artifacts": {k: str(v) for k, v in result.artifacts.items()},
        "errors": result.errors,
    }
```

#### Task 7.2: Add Cache Tool Definition

**File:** `src/glintefy/servers/review_tools.py` (modify)

Add cache tool definition to the tool list.

---

### Phase 8: Configuration

#### Task 8.1: Add to defaultconfig.toml

**File:** `src/glintefy/defaultconfig.toml` (modify)

```toml
[review.cache]
# Cache analysis settings
cache_size = 128                    # LRU cache maxsize
hit_rate_threshold = 20.0           # Minimum cache hit rate % (batch screening)
speedup_threshold = 5.0             # Minimum speedup % (individual validation)
min_calls = 100                     # Minimum calls for hotspot detection
min_cumtime = 0.1                   # Minimum cumulative time for hotspot (seconds)
```

---

### Phase 9: Testing

#### Task 9.1: Unit Tests

Create comprehensive test suite:

```
tests/subservers/review/cache/
├── test_pure_function_detector.py
├── test_hotspot_analyzer.py
├── test_batch_screener.py
├── test_individual_validator.py
└── test_cache_subserver.py
```

#### Task 9.2: Integration Tests

Test full pipeline:

```python
# tests/integration/test_cache_analysis.py
def test_full_cache_analysis_pipeline():
    """Test complete cache analysis workflow."""
    # Setup: Create sample code with pure functions
    # Run: Execute full pipeline
    # Assert: Verify recommendations are generated
```

---

### Phase 10: Documentation

#### Task 10.1: Update Documentation

Files to update:
- `README.md` - Add cache analysis to features
- `docs/review_system.md` - Document cache analysis
- `CLAUDE.md` - Add cache analysis guidelines

---

## 📊 Success Criteria

- ✅ All unit tests passing
- ✅ Integration tests passing
- ✅ Cache analysis completes in reasonable time (< 30 min for typical codebase)
- ✅ Recommendations are accurate (manual validation on sample projects)
- ✅ Configuration properly loaded from config file
- ✅ MCP tool definitions working
- ✅ Documentation complete

---

## 🚀 Execution Order

1. **Phase 1-2:** Core data structures + pure function detection (Day 1)
2. **Phase 3:** Hotspot analysis (Day 1)
3. **Phase 4-5:** Batch screening + individual validation (Day 2)
4. **Phase 6:** Main CacheSubServer integration (Day 2)
5. **Phase 7-8:** ReviewMCPServer integration + config (Day 3)
6. **Phase 9:** Testing (Day 3-4)
7. **Phase 10:** Documentation (Day 4)

**Estimated Total Time:** 4 days

---

## 📝 Notes

- **Dependencies:** Requires `perf` sub-server to run first (generates test_profile.prof)
- **Test Suite Requirement:** Project must have functional pytest test suite
- **Performance Impact:** Batch + individual testing will run test suite multiple times
- **Python 3.13+:** Required for AST features and profiling tools
