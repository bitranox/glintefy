"""Data models for cache analysis.

These dataclasses represent results at each stage of the cache analysis pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExistingCacheCandidate:
    """Function that already has @lru_cache decorator."""

    file_path: Path
    function_name: str
    line_number: int
    module_path: str
    current_maxsize: int | None  # None means unbounded


@dataclass
class PureFunctionCandidate:
    """Result from AST analysis - potentially cacheable function."""

    file_path: Path
    function_name: str
    line_number: int
    is_pure: bool
    expense_indicators: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation."""
        status = "PURE" if self.is_pure else "IMPURE"
        indicators = ", ".join(self.expense_indicators) if self.expense_indicators else "none"
        return f"{status}: {self.function_name} at {self.file_path}:{self.line_number} (indicators: {indicators})"


@dataclass
class Hotspot:
    """Function called frequently with significant time cost."""

    file_path: Path
    function_name: str
    line_number: int
    call_count: int
    cumulative_time: float
    time_per_call: float

    def __str__(self) -> str:
        """String representation."""
        return f"{self.function_name} at {self.file_path}:{self.line_number} ({self.call_count} calls, {self.cumulative_time:.4f}s cumtime)"


@dataclass
class CacheCandidate:
    """High-priority candidate - both pure AND hot."""

    file_path: Path
    function_name: str
    line_number: int
    module_path: str
    call_count: int
    cumulative_time: float
    expense_indicators: list[str] = field(default_factory=list)
    priority: str = "MEDIUM"

    def __str__(self) -> str:
        """String representation."""
        indicators = ", ".join(self.expense_indicators) if self.expense_indicators else "none"
        return (
            f"{self.priority}: {self.function_name} ({self.module_path}) "
            f"at {self.file_path}:{self.line_number} "
            f"(calls={self.call_count}, cumtime={self.cumulative_time:.4f}s, indicators={indicators})"
        )


@dataclass
class BatchScreeningResult:
    """Results from batch cache testing."""

    candidate: CacheCandidate
    hits: int
    misses: int
    hit_rate: float
    maxsize: int
    currsize: int
    passed_screening: bool

    def __str__(self) -> str:
        """String representation."""
        status = "PASS" if self.passed_screening else "FAIL"
        return f"{status}: {self.candidate.function_name} (hit_rate={self.hit_rate:.1f}%, hits={self.hits}, misses={self.misses})"


@dataclass
class IndividualValidationResult:
    """Results from individual cache testing."""

    candidate: CacheCandidate
    baseline_time: float
    cached_time: float
    speedup_percent: float
    hits: int
    misses: int
    hit_rate: float
    recommendation: str
    rejection_reason: str | None = None

    def __str__(self) -> str:
        """String representation."""
        if self.recommendation == "APPLY":
            return f"RECOMMEND: {self.candidate.function_name} (speedup={self.speedup_percent:.1f}%, hit_rate={self.hit_rate:.1f}%)"
        return f"REJECT: {self.candidate.function_name} ({self.rejection_reason})"


@dataclass
class CacheRecommendation:
    """Final recommendation for production deployment."""

    file_path: Path
    function_name: str
    line_number: int
    module_path: str
    decorator: str
    expected_speedup: float
    cache_hit_rate: float
    evidence: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.function_name} at {self.file_path}:{self.line_number}\n"
            f"  Apply: {self.decorator}\n"
            f"  Expected speedup: {self.expected_speedup:.1f}%\n"
            f"  Cache hit rate: {self.cache_hit_rate:.1f}%"
        )


@dataclass
class ExistingCacheEvaluation:
    """Evaluation of an existing @lru_cache decorator."""

    candidate: ExistingCacheCandidate
    hits: int
    misses: int
    hit_rate: float
    recommendation: str  # "KEEP", "REMOVE", "ADJUST_SIZE"
    reason: str | None = None
    suggested_maxsize: int | None = None
