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

# Import from parent level (cache_subserver.py is at review level)
from btx_fix_mcp.subservers.review.cache_subserver import CacheSubServer
from btx_fix_mcp.subservers.review.cache.cache_models import (
    BatchScreeningResult,
    CacheCandidate,
    CacheRecommendation,
    ExistingCacheCandidate,
    ExistingCacheEvaluation,
    Hotspot,
    IndividualValidationResult,
    PureFunctionCandidate,
)
from btx_fix_mcp.subservers.review.cache.source_patcher import SourcePatcher

__all__ = [
    "CacheSubServer",
    "PureFunctionCandidate",
    "Hotspot",
    "CacheCandidate",
    "BatchScreeningResult",
    "IndividualValidationResult",
    "CacheRecommendation",
    "ExistingCacheCandidate",
    "ExistingCacheEvaluation",
    "SourcePatcher",
]
