"""Cache analysis sub-module.

Identifies caching opportunities using hybrid approach:
1. AST analysis - identify pure functions
2. Profiling cross-reference - find hot spots
3. Batch screening - filter by hit rate
4. Individual validation - measure precise impact

Uses temporary source modification instead of monkey-patching:
- subprocess.run() creates fresh Python interpreter
- Monkey-patches in parent are invisible to subprocess
- Source modifications persist across process boundary
"""

# Note: CacheSubServer is at parent level (cache_subserver.py) to avoid circular imports
# Import from glintefy.subservers.review.cache_subserver directly
from glintefy.subservers.review.cache.cache_models import (
    BatchScreeningResult,
    CacheCandidate,
    CacheRecommendation,
    ExistingCacheCandidate,
    ExistingCacheEvaluation,
    Hotspot,
    IndividualValidationResult,
    PureFunctionCandidate,
)
from glintefy.subservers.review.cache.source_patcher import SourcePatcher

__all__ = [
    "BatchScreeningResult",
    "CacheCandidate",
    "CacheRecommendation",
    "ExistingCacheCandidate",
    "ExistingCacheEvaluation",
    "Hotspot",
    "IndividualValidationResult",
    "PureFunctionCandidate",
    "SourcePatcher",
]
