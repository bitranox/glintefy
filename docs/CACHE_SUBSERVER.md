# Cache Subserver Documentation

> Identifies `@lru_cache` optimization opportunities using AST analysis and runtime profiling.

## Overview

The cache subserver analyzes Python code to find functions that would benefit from memoization with `@lru_cache`. It uses a hybrid approach combining static analysis with optional runtime profiling data.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CacheSubServer                                │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │ PureFunctionDetector │    │ HotspotAnalyzer │    │ BatchScreener │ │
│  │ (AST Analysis)    │    │ (Profile Data)   │    │ (Hit Rate)    │ │
│  └────────┬─────────┘    └────────┬─────────┘    └───────┬───────┘ │
│           │                       │                       │         │
│           └───────────┬───────────┘                       │         │
│                       │                                   │         │
│                       ▼                                   │         │
│              Cross-Reference                              │         │
│           (Pure + Hot = Candidate)                        │         │
│                       │                                   │         │
│                       ▼                                   │         │
│              Batch Screening ◄────────────────────────────┘         │
│                       │                                             │
│                       ▼                                             │
│              Individual Validation                                  │
│                       │                                             │
│                       ▼                                             │
│              Recommendations                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. PureFunctionDetector

Identifies functions that are safe to cache using AST analysis.

**Criteria for Pure Functions:**
- No I/O operations (`print`, `open`, `read`, `write`)
- No non-deterministic calls (`random`, `now`, `uuid`)
- No global/nonlocal state modification
- Deterministic output for same inputs

**Expense Indicators Detected:**
- Nested loops
- Recursion
- Cryptographic operations
- Complex comprehensions

### 2. HotspotAnalyzer

Analyzes cProfile data to find performance-critical functions.

**Configuration:**
- `min_calls`: Minimum call count threshold (default: 100)
- `min_cumtime`: Minimum cumulative time in seconds (default: 0.1)

**Output:**
- Function call counts
- Cumulative execution time
- Time per call

### 3. BatchScreener

Tests cache candidates by temporarily applying `@lru_cache` decorators.

**Process:**
1. Backs up original source files (in-memory)
2. Applies cache decorators to all candidates
3. Runs test suite to collect cache statistics
4. Measures hit/miss rates
5. Restores original code from backup

> **Note:** No git dependency required. Uses in-memory backup for safe source modification.

**Configuration:**
- `cache_size`: LRU cache maxsize (default: 128)
- `hit_rate_threshold`: Minimum hit rate % to pass (default: 20%)

### 4. IndividualValidator

Validates candidates that passed batch screening with precise timing.

**Process:**
1. Measures baseline performance (without cache)
2. Applies cache decorator
3. Measures cached performance
4. Calculates speedup percentage

**Configuration:**
- `speedup_threshold`: Minimum speedup % required (default: 5%)
- `num_runs`: Number of runs to average (default: 3)

## Usage

### Basic Usage

```python
from pathlib import Path
from glintefy.subservers.review.cache_subserver import CacheSubServer

server = CacheSubServer(
    input_dir=Path("LLM-CONTEXT/review/scope"),
    output_dir=Path("LLM-CONTEXT/review/cache"),
    repo_path=Path.cwd(),
)

result = server.run()
print(result.summary)
```

### With Custom Configuration

```python
server = CacheSubServer(
    input_dir=Path("LLM-CONTEXT/review/scope"),
    output_dir=Path("LLM-CONTEXT/review/cache"),
    repo_path=Path.cwd(),
    cache_size=256,           # Larger cache
    hit_rate_threshold=30.0,  # Stricter hit rate
    speedup_threshold=10.0,   # Require 10% speedup
    min_calls=50,             # Lower call threshold
)
```

### Via CLI

```bash
# Run cache analysis
python -m glintefy review cache

# Profile your application first, then analyze
python -m glintefy review profile -- python my_app.py
python -m glintefy review cache
```

## Getting Runtime Cache Statistics

### Why Runtime Profiling?

Static analysis estimates cache benefit by counting call sites in code. Runtime profiling provides **actual data**:

| Metric | Static Analysis | Runtime Profiling |
|--------|-----------------|-------------------|
| Call frequency | Call sites in code | Actual runtime calls |
| Hit rate | Cannot measure | Exact hits/misses |
| Performance impact | Estimated | Measured |
| Accuracy | Approximate | Precise |

### Easy Profiling with CLI (Recommended)

The simplest way to profile your application:

```bash
# Profile any Python command
python -m glintefy review profile -- python my_app.py

# Profile your test suite
python -m glintefy review profile -- pytest tests/

# Profile a module
python -m glintefy review profile -- python -m my_module

# After profiling, run cache analysis
python -m glintefy review cache
```

The `review profile` command automatically:
- Wraps your command with cProfile
- Saves the profile to `LLM-CONTEXT/glintefy/review/perf/test_profile.prof`
- Works with any Python script, module, or pytest

### Manual Profiling (Alternative)

For more control, create a custom profiling script:

```python
# profile_app.py
import cProfile
from pathlib import Path

def main():
    """Your application entry point."""
    from my_app import run_application
    run_application()

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()

    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")
```

### Profile Test Suite

Use your test suite as a proxy for real usage:

```bash
# Easy way (recommended)
python -m glintefy review profile -- pytest tests/ -v

# Or manually
python -m cProfile -o LLM-CONTEXT/glintefy/review/perf/test_profile.prof -m pytest tests/ -v
```

> **⚠️ Limitation**: Test suite profiling may give inaccurate cache statistics because:
> - Pytest often clears `@lru_cache` between tests (via fixtures or `cache_clear()`)
> - Each test runs in isolation, so cache hits don't accumulate across tests
> - Test data is often synthetic with high uniqueness (low cache hit potential)
>
> For accurate cache analysis, prefer profiling your **actual application workload** rather than the test suite.

### Profile Real Application Workloads

Profile your actual application with realistic data:

```bash
# Profile a web application request handler
python -m glintefy review profile -- python -c "
from my_app import app
from werkzeug.test import Client

client = Client(app)
# Simulate typical user workflow
for i in range(100):
    client.get('/api/users')
    client.get('/api/products')
    client.post('/api/orders', json={'product_id': i % 10})
"

# Profile a data processing script
python -m glintefy review profile -- python scripts/process_data.py --input data/sample.csv

# Profile a CLI tool with typical arguments
python -m glintefy review profile -- python -m my_cli analyze --verbose reports/*.json

# Profile with cProfile directly for more control
python -m cProfile -o LLM-CONTEXT/glintefy/review/perf/test_profile.prof -c "
import my_module
# Run realistic workload
for data in my_module.load_production_samples(1000):
    my_module.process(data)
"
```

**Tips for realistic profiling:**
- Use production-like data volumes (not just test fixtures)
- Include common user workflows, not just edge cases
- Run multiple iterations to capture cache behavior
- Profile during typical load, not just startup

### Step 3: Collect Cache Statistics from Existing Caches

For functions already decorated with `@lru_cache`, you can collect statistics after running your application:

```python
# collect_cache_stats.py
from functools import lru_cache
import json
from pathlib import Path

# Import your cached functions
from my_module import my_cached_function

def collect_cache_info(func) -> dict:
    """Extract cache statistics from an lru_cache decorated function."""
    try:
        info = func.cache_info()
        total = info.hits + info.misses
        hit_rate = (info.hits / total * 100) if total > 0 else 0.0

        return {
            "hits": info.hits,
            "misses": info.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "maxsize": info.maxsize,
            "currsize": info.currsize,
        }
    except AttributeError:
        return {"error": "Not an lru_cache decorated function"}

# After running your application workload...
stats = collect_cache_info(my_cached_function)
print(json.dumps(stats, indent=2))

# Output:
# {
#   "hits": 1234,
#   "misses": 56,
#   "hit_rate_percent": 95.66,
#   "maxsize": 128,
#   "currsize": 56
# }
```

### Step 4: Analyze with Profiling Data

Once profiling data exists, run cache analysis:

```bash
python -m glintefy review cache
```

The cache subserver automatically detects and uses:
- `LLM-CONTEXT/glintefy/review/perf/test_profile.prof`

## Understanding Results

### Existing Cache Evaluations

For functions already using `@lru_cache`:

```json
{
  "file": "src/my_module.py",
  "function": "expensive_computation",
  "line": 42,
  "current_maxsize": 128,
  "recommendation": "KEEP",
  "reason": "Production data: Good hit rate (85.3%)",
  "hits": 1234,
  "misses": 213,
  "hit_rate_percent": 85.3
}
```

**Recommendation Values:**
- `KEEP`: Cache is effective, maintain current configuration
- `REMOVE`: Cache has low hit rate (<10%), remove the decorator
- `ADJUST_SIZE`: Cache is effective but maxsize is oversized

### New Cache Candidates

For pure functions that could benefit from caching:

```json
{
  "file": "src/utils.py",
  "function": "calculate_hash",
  "line": 156,
  "priority": "HIGH",
  "call_count": 5000,
  "cumulative_time": 2.5,
  "expense_indicators": ["nested_loops", "crypto"],
  "recommendation": "ADD_CACHE",
  "suggested_maxsize": 128
}
```

**Priority Levels:**
- `HIGH`: Many calls (≥500) + significant time (≥1s) + expensive operations
- `MEDIUM`: Decent calls (≥200) or time (≥0.5s)
- `LOW`: Meets minimum thresholds

## Profile Freshness Validation

The cache subserver validates that profiling data is current and matches the codebase:

### Time-Based Freshness

Profile data older than `max_profile_age_hours` (default: 24 hours) triggers a warning:

```
⚠️ Profile data is 48.3 hours old (threshold: 24 hours).
Consider regenerating with: python -m glintefy review profile -- pytest tests/
```

### Code-Based Validation

The subserver compares profiled function names against current code:

```
⚠️ Profile contains 5 functions that no longer exist in codebase (matched: 142).
Profile may be outdated.
```

This detects when:
- Functions have been renamed or deleted
- Modules have been restructured
- Profile was generated from a different branch

### Keeping Profiles Fresh

```bash
# Regenerate profile after code changes
python -m glintefy review profile -- pytest tests/
python -m glintefy review cache

# Or set up a pre-commit hook to auto-profile
```

## Configuration Reference

### Config File (`defaultconfig.toml`)

```toml
[review.cache]
cache_size = 128              # Default LRU cache maxsize
hit_rate_threshold = 20.0     # Minimum hit rate % to recommend
speedup_threshold = 5.0       # Minimum speedup % required
min_calls = 100               # Minimum calls for hotspot detection
min_cumtime = 0.1             # Minimum cumulative time (seconds)
test_timeout = 300            # Test suite timeout (seconds)
num_runs = 3                  # Runs for timing average
max_profile_age_hours = 24.0  # Maximum profile age before warning
```

### Environment Variables

```bash
export GLINTEFY_REVIEW_CACHE_CACHE_SIZE=256
export GLINTEFY_REVIEW_CACHE_HIT_RATE_THRESHOLD=30.0
export GLINTEFY_REVIEW_CACHE_MAX_PROFILE_AGE_HOURS=48.0
```

## Output Files

The cache subserver generates:

| File | Description |
|------|-------------|
| `summary.md` | Human-readable analysis summary |
| `pure_functions.json` | All detected pure functions |
| `hotspots.json` | Performance hotspots from profiling |
| `cache_candidates.json` | Functions recommended for caching |
| `existing_cache_evaluations.json` | Analysis of current `@lru_cache` usage |
| `screening_results.json` | Batch screening hit rate data |
| `validation_results.json` | Individual timing validation data |
| `recommendations.json` | Final recommendations with evidence |

## Best Practices

### 1. Profile Representative Workloads

Profile your application with realistic usage patterns:

```python
# Good: Representative workload
def profile_realistic():
    # Process typical data volumes
    for batch in get_production_batches(sample_size=1000):
        process_batch(batch)

    # Include common operations
    for user_id in sample_user_ids:
        get_user_profile(user_id)
        get_user_permissions(user_id)
```

### 2. Monitor Cache Effectiveness

Add logging to track cache performance in production:

```python
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

@lru_cache(maxsize=128)
def expensive_operation(key):
    result = do_computation(key)
    return result

def log_cache_stats():
    info = expensive_operation.cache_info()
    logger.info(
        f"Cache stats: hits={info.hits}, misses={info.misses}, "
        f"hit_rate={info.hits/(info.hits+info.misses)*100:.1f}%"
    )
```

### 3. Clear Caches When Appropriate

Remember to clear caches when underlying data changes:

```python
@lru_cache(maxsize=128)
def get_config_value(key):
    return load_from_database(key)

def update_config(key, value):
    save_to_database(key, value)
    get_config_value.cache_clear()  # Invalidate cache
```

### 4. Choose Appropriate Cache Sizes

```python
# Small, frequently accessed data
@lru_cache(maxsize=32)
def get_constant(name): ...

# Larger working set
@lru_cache(maxsize=256)
def compute_hash(data): ...

# Unbounded (use carefully!)
@lru_cache(maxsize=None)
def factorial(n): ...
```

## Troubleshooting

### "No profiling data found"

This is normal for first run. Cache analysis uses static analysis as fallback. To enable profiling:

```bash
# Easy way
python -m glintefy review profile -- pytest tests/

# Verify file exists
ls LLM-CONTEXT/glintefy/review/perf/test_profile.prof
```

### "Profile data is X hours old"

Delete the old profile and regenerate:

```bash
# Delete old profile
python -m glintefy review clean -s profile

# Regenerate
python -m glintefy review profile -- pytest tests/
```

To increase the threshold:
```bash
export GLINTEFY_REVIEW_CACHE_MAX_PROFILE_AGE_HOURS=72.0
```

### "Profile contains X functions that no longer exist"

The profile was generated before recent code changes. Clean and regenerate:

```bash
python -m glintefy review clean -s profile
python -m glintefy review profile -- pytest tests/
python -m glintefy review cache
```

### Cleaning Up Analysis Data

Remove old analysis results to start fresh:

```bash
# Clean all review data
python -m glintefy review clean

# Clean specific subserver output
python -m glintefy review clean -s cache     # Cache analysis only
python -m glintefy review clean -s profile   # Profile data only
python -m glintefy review clean -s quality   # Quality analysis only

# Preview what would be deleted
python -m glintefy review clean --dry-run
```

### "Cache statistics show 0 hits/misses"

Causes:
- Cached function not called during profiling
- Module not imported during execution
- `cache_clear()` called after execution

Solution: Ensure profiling workload exercises the cached functions.

### "Low hit rate despite many calls"

Investigate cache key patterns:

```python
@lru_cache(maxsize=128)
def process(data):  # Problem: unhashable or unique args
    ...

# Check if arguments are repeating
print(f"Unique args: {len(set(all_args))}")
print(f"Total calls: {len(all_args)}")
```

### "Static vs Runtime analysis disagree"

Expected behavior. Static analysis counts **call sites**, runtime counts **actual calls**:

```python
# Static: 1 call site
# Runtime: 10,000 calls
for i in range(10000):
    result = cached_function(i % 100)  # Only 100 unique args!
```

Runtime data is more accurate for optimization decisions.

## See Also

- [Cache Profiling Guide](cache_profiling_guide.md) - Detailed profiling workflows
- [Getting Started](GETTING_STARTED.md) - Project overview
- [Architecture](ARCHITECTURE_SUMMARY.md) - System design
