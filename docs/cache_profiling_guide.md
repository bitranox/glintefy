# Cache Profiling Guide

## Overview

This guide explains how to collect real-world profiling data from your application and use it to make data-driven cache optimization decisions.

## Why Profile Your Application?

Static code analysis (default) makes recommendations based on **call frequency** - how many times a function is called in the codebase. This is useful but doesn't capture:

- **Runtime call patterns**: How many times functions are actually called during execution
- **Cache hit rates**: How often cached values are reused vs recomputed
- **Performance impact**: Which functions consume the most CPU time
- **Hot paths**: Functions called repeatedly in loops or high-traffic code

**Production profiling data** gives you the real story about which caches are worth keeping.

## How Cache Analysis Uses Runtime Data

The cache subserver can use two types of runtime data:

### 1. cProfile Data (Function-Level Profiling)

Captures which functions are called, how often, and how long they take:

```
ncalls  tottime  percall  cumtime  percall filename:lineno(function)
5000    0.125    0.000    2.500    0.001 utils.py:42(expensive_calc)
```

Used for: **Identifying cache candidates** (pure functions that are hot spots)

### 2. lru_cache Statistics (Cache-Level Metrics)

Captures actual cache performance for existing `@lru_cache` decorators:

```python
>>> my_cached_func.cache_info()
CacheInfo(hits=1234, misses=56, maxsize=128, currsize=56)
```

Used for: **Evaluating existing caches** (keep, remove, or adjust size)

## Quick Start: 2-Step Workflow

### Step 1: Profile Your Application (Easy CLI Method)

The simplest way to profile is using the built-in CLI:

```bash
# Profile any Python command
python -m glintefy review profile -- python my_app.py

# Profile your test suite
python -m glintefy review profile -- pytest tests/

# Profile a module
python -m glintefy review profile -- python -m my_module
```

The `review profile` command automatically:
- Wraps your command with cProfile
- Saves the profile to `LLM-CONTEXT/glintefy/review/perf/test_profile.prof`
- Works with any Python script, module, or pytest

### Step 2: Run Cache Analysis

With profiling data available, cache analysis automatically detects and uses it:

```bash
python -m glintefy review cache
```

Or via the MCP server:

```python
from glintefy.servers.review import ReviewMCPServer

server = ReviewMCPServer(repo_path=".")
result = server.run_cache()
print(result["summary"])
```

### Cleaning Up Old Profile Data

Before re-profiling, you can clean old data:

```bash
# Delete old profile only
python -m glintefy review clean -s profile

# Delete all cache analysis data
python -m glintefy review clean -s cache

# Delete all review data
python -m glintefy review clean

# Preview what would be deleted
python -m glintefy review clean --dry-run
```

## Detailed Workflows

### Workflow 1: Profile CLI Application

For command-line applications, wrap your main execution:

```python
# profile_my_app.py
import cProfile
import pstats
from pathlib import Path
import sys

def main():
    """Your application's main function."""
    # Your application logic here
    pass

if __name__ == "__main__":
    # Enable profiling
    profiler = cProfile.Profile()
    profiler.enable()

    # Run application
    try:
        main()
    finally:
        profiler.disable()

        # Save profiling data
        output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
        output_dir.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(output_dir / "test_profile.prof")

        print(f"\n✓ Profiling data saved", file=sys.stderr)
```

Run it:
```bash
python profile_my_app.py
python -m glintefy review cache
```

### Workflow 2: Profile Web Application

For web servers (Flask, FastAPI, Django), profile a representative sample:

```python
# profile_web_app.py
import cProfile
from pathlib import Path
from your_app import app, client  # Your test client

def simulate_workload():
    """Simulate typical user requests."""
    # Example: FastAPI test client
    response = client.get("/api/users")
    response = client.post("/api/data", json={"key": "value"})
    response = client.get("/api/search?q=example")

    # Repeat to simulate realistic traffic
    for i in range(100):
        client.get(f"/api/items/{i}")

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    simulate_workload()

    profiler.disable()

    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
```

### Workflow 3: Profile Data Processing Pipeline

For batch processing or ETL pipelines:

```python
# profile_pipeline.py
import cProfile
from pathlib import Path
from your_pipeline import process_batch

def run_typical_batch():
    """Run a representative batch of data."""
    # Process sample data that represents your typical workload
    input_files = list(Path("data/sample").glob("*.csv"))
    process_batch(input_files)

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    run_typical_batch()

    profiler.disable()

    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
```

### Workflow 4: Profile Test Suite (Limited Accuracy)

You can use your test suite as a quick proxy, but be aware of limitations:

```bash
# Easy way
python -m glintefy review profile -- pytest tests/ -v
```

Or manually:

```python
# profile_tests.py
import cProfile
from pathlib import Path
import pytest

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Run test suite
    pytest.main([
        "tests/",
        "-v",
        "--tb=short",
    ])

    profiler.disable()

    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
```

> **⚠️ Important Limitation**: Test suite profiling often gives **inaccurate cache statistics**:
>
> | Issue | Why It Happens |
> |-------|----------------|
> | **Low hit rates** | Caches are often cleared between tests via `cache_clear()` or fixtures |
> | **Missing data** | Tests run in isolation, so cache hits don't accumulate across test functions |
> | **Synthetic patterns** | Test data often has high uniqueness (random IDs, unique inputs) |
> | **Unrealistic workloads** | Tests exercise edge cases, not typical user workflows |
>
> **Recommendation**: Use test suite profiling for quick initial analysis, but profile your **actual application workload** for production cache optimization decisions.

## Understanding Profiling Results

### Cache Statistics from Production Data

When profiling data is available, cache analysis will show:

```json
{
  "file": "src/your_module.py",
  "function": "expensive_computation",
  "recommendation": "KEEP",
  "reason": "Production data: Good hit rate (85.3%)",
  "evidence": {
    "hits": 1234,
    "misses": 213,
    "hit_rate_percent": 85.3
  }
}
```

### Static Analysis (No Profiling Data)

Without profiling data, you'll see:

```json
{
  "file": "src/your_module.py",
  "function": "expensive_computation",
  "recommendation": "KEEP",
  "reason": "Static analysis: Function called 15 times in codebase - likely benefits from caching",
  "evidence": {
    "hits": 0,
    "misses": 0,
    "hit_rate_percent": 0.0
  }
}
```

## Profiling Data Location

The cache analysis expects profiling data at:

```
<repo_root>/LLM-CONTEXT/glintefy/review/perf/test_profile.prof
```

You can also specify a custom location when creating the cache sub-server:

```python
from glintefy.subservers.review.cache_subserver import CacheSubServer
from pathlib import Path

server = CacheSubServer(
    output_dir=Path("LLM-CONTEXT/glintefy/review/cache"),
    profile_path=Path("custom/path/to/profile.prof"),  # Custom location
)

result = server.run()
```

## Best Practices

### 1. Representative Workload

Profile your application with a **realistic workload**:

- ✅ Use real data samples (anonymized if needed)
- ✅ Include typical user operations
- ✅ Run long enough to hit steady state
- ❌ Don't just run trivial examples
- ❌ Don't profile just startup code

### 2. Multiple Scenarios

Consider profiling different scenarios:

```python
# profile_scenarios.py
import cProfile
from pathlib import Path

scenarios = [
    ("heavy_load", simulate_heavy_load),
    ("light_load", simulate_light_load),
    ("edge_cases", simulate_edge_cases),
]

for name, scenario_func in scenarios:
    profiler = cProfile.Profile()
    profiler.enable()

    scenario_func()

    profiler.disable()

    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save with scenario name
    profiler.dump_stats(output_dir / f"{name}_profile.prof")

    print(f"✓ Saved {name} profiling data")

# Merge profiles (optional)
import pstats
stats = pstats.Stats(output_dir / "heavy_load_profile.prof")
stats.add(output_dir / "light_load_profile.prof")
stats.add(output_dir / "edge_cases_profile.prof")
stats.dump_stats(output_dir / "test_profile.prof")

print("✓ Merged all scenarios into test_profile.prof")
```

### 3. Continuous Profiling

Update profiling data periodically as your application evolves:

```bash
# Add to your CI/CD pipeline or development workflow
python scripts/profile_application.py  # Run profiling
python -m glintefy review cache  # Analyze with fresh data
```

### 4. Cache Hit Rate Debugging

If you see low hit rates, investigate:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def my_function(arg):
    return expensive_computation(arg)

# After running your workload
info = my_function.cache_info()
print(f"Hits: {info.hits}")
print(f"Misses: {info.misses}")
print(f"Hit rate: {info.hits / (info.hits + info.misses) * 100:.1f}%")
print(f"Cache size: {info.currsize}/{info.maxsize}")

# Low hit rate? Check:
# 1. Are arguments truly repeated?
# 2. Is maxsize too small?
# 3. Are arguments hashable and stable?
```

## Troubleshooting

### "No profiling data found"

This is normal! It means the cache analysis will use static code analysis instead. To use profiling data:

1. Verify file exists: `ls -la LLM-CONTEXT/glintefy/review/perf/test_profile.prof`
2. Check file is valid: `python -c "import pstats; pstats.Stats('LLM-CONTEXT/glintefy/review/perf/test_profile.prof').print_stats()"`
3. Re-run profiling if file is missing or corrupt

### "Cache statistics show 0 hits/misses"

This happens when:

1. **Cached function not called**: Function exists but wasn't executed during profiling
2. **Import issue**: Module wasn't imported during profiling
3. **Cache cleared**: Code called `.cache_clear()` after execution

Solution: Ensure your profiling workload actually calls the cached functions.

### "Static analysis gives different result than profiling"

This is expected! Static analysis counts **call sites in code**, profiling counts **runtime calls**:

```python
# Static analysis sees: 1 call site
for i in range(1000):
    result = cached_function(i)  # But runs 1000 times!
```

Profiling data is more accurate for cache optimization decisions.

## Advanced: Custom Cache Statistics

For even more accurate analysis, you can instrument your caches to track statistics:

```python
from functools import lru_cache, wraps

def tracked_cache(maxsize=128):
    """LRU cache that maintains statistics across imports."""
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)

        # Statistics survive module reload
        if not hasattr(cached_func, '_call_count'):
            cached_func._call_count = 0

        @wraps(func)
        def wrapper(*args, **kwargs):
            cached_func._call_count += 1
            return cached_func(*args, **kwargs)

        # Expose original cache_info
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        wrapper._call_count = cached_func._call_count

        return wrapper
    return decorator

# Usage
@tracked_cache(maxsize=128)
def my_function(arg):
    return expensive_computation(arg)
```

## Example: Full End-to-End Workflow

```bash
# 1. Create profiling script
cat > profile_app.py << 'EOF'
import cProfile
from pathlib import Path
from my_app import run_application

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your application with typical workload
    run_application()

    profiler.disable()

    # Save profiling data
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
EOF

# 2. Run profiling
python profile_app.py

# 3. Run cache analysis with profiling data
python -m glintefy review cache

# 4. Review results
cat LLM-CONTEXT/glintefy/review/cache/existing_cache_evaluations.json
```

## Collecting Runtime Cache Statistics

### Method 1: Inspect Existing Caches After Workload

After running your application, inspect cache statistics directly:

```python
#!/usr/bin/env python3
"""Collect cache statistics from existing @lru_cache decorators."""

import importlib
import json
from pathlib import Path

def get_cache_stats(module_path: str, function_name: str) -> dict:
    """Get cache statistics from an lru_cache decorated function.

    Args:
        module_path: Dotted module path (e.g., "myapp.utils")
        function_name: Name of the cached function

    Returns:
        Dictionary with cache statistics
    """
    module = importlib.import_module(module_path)
    func = getattr(module, function_name)

    try:
        info = func.cache_info()
        total = info.hits + info.misses
        hit_rate = (info.hits / total * 100) if total > 0 else 0.0

        return {
            "module": module_path,
            "function": function_name,
            "hits": info.hits,
            "misses": info.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "maxsize": info.maxsize,
            "currsize": info.currsize,
            "utilization_percent": round(info.currsize / info.maxsize * 100, 2) if info.maxsize else 0,
        }
    except AttributeError:
        return {"error": f"{function_name} is not an lru_cache decorated function"}


# Example usage after running your application:
if __name__ == "__main__":
    # List your cached functions here
    cached_functions = [
        ("myapp.database", "get_user"),
        ("myapp.utils", "compute_hash"),
        ("myapp.config", "load_settings"),
    ]

    results = []
    for module_path, func_name in cached_functions:
        stats = get_cache_stats(module_path, func_name)
        results.append(stats)
        print(f"{module_path}.{func_name}:")
        print(f"  Hit rate: {stats.get('hit_rate_percent', 'N/A')}%")
        print(f"  Hits/Misses: {stats.get('hits', 0)}/{stats.get('misses', 0)}")
        print()

    # Save to JSON for analysis
    Path("cache_stats.json").write_text(json.dumps(results, indent=2))
```

### Method 2: Profile with Cache Stats Collection

Combine cProfile with cache statistics collection:

```python
#!/usr/bin/env python3
"""Profile application and collect cache statistics."""

import cProfile
import json
from pathlib import Path

def main():
    """Run your application workload."""
    from myapp import run_application
    run_application()

def collect_all_cache_stats():
    """Collect statistics from all @lru_cache functions."""
    from myapp.database import get_user, get_permissions
    from myapp.utils import compute_hash

    results = {}
    for name, func in [
        ("database.get_user", get_user),
        ("database.get_permissions", get_permissions),
        ("utils.compute_hash", compute_hash),
    ]:
        try:
            info = func.cache_info()
            total = info.hits + info.misses
            results[name] = {
                "hits": info.hits,
                "misses": info.misses,
                "hit_rate": round(info.hits / total * 100, 2) if total > 0 else 0,
                "maxsize": info.maxsize,
                "currsize": info.currsize,
            }
        except AttributeError:
            pass

    return results

if __name__ == "__main__":
    # Profile the application
    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()

    # Save cProfile data
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    # Collect and save cache statistics
    cache_stats = collect_all_cache_stats()
    (output_dir / "cache_stats.json").write_text(json.dumps(cache_stats, indent=2))

    print("Profiling data and cache stats saved!")
    print("\nCache Statistics:")
    for name, stats in cache_stats.items():
        print(f"  {name}: {stats['hit_rate']}% hit rate "
              f"({stats['hits']} hits, {stats['misses']} misses)")
```

### Method 3: Continuous Cache Monitoring

Add cache monitoring to your production application:

```python
import logging
import threading
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

# Registry of cached functions to monitor
_cache_registry = []

def monitored_cache(maxsize=128):
    """LRU cache decorator that registers function for monitoring."""
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        _cache_registry.append((func.__qualname__, cached_func))
        return cached_func
    return decorator

def log_cache_stats():
    """Log statistics for all registered caches."""
    for name, func in _cache_registry:
        info = func.cache_info()
        total = info.hits + info.misses
        hit_rate = (info.hits / total * 100) if total > 0 else 0
        logger.info(
            f"Cache {name}: "
            f"hit_rate={hit_rate:.1f}% "
            f"hits={info.hits} misses={info.misses} "
            f"size={info.currsize}/{info.maxsize}"
        )

def start_cache_monitor(interval_seconds=300):
    """Start background thread to log cache stats periodically."""
    def monitor():
        while True:
            time.sleep(interval_seconds)
            log_cache_stats()

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

# Usage in your application:
@monitored_cache(maxsize=256)
def expensive_operation(key):
    return do_computation(key)

# Start monitoring when app starts
start_cache_monitor(interval_seconds=60)  # Log every minute
```

## Interpreting Cache Statistics

### Hit Rate Guidelines

| Hit Rate | Interpretation | Recommendation |
|----------|----------------|----------------|
| **>80%** | Excellent | Keep cache, possibly increase maxsize |
| **50-80%** | Good | Keep cache, current config is reasonable |
| **20-50%** | Marginal | Monitor performance, may need tuning |
| **<20%** | Poor | Consider removing cache |

### Cache Utilization

```python
info = my_func.cache_info()
utilization = info.currsize / info.maxsize * 100

if utilization > 90:
    print("Cache is nearly full - consider increasing maxsize")
elif utilization < 30:
    print("Cache is underutilized - consider decreasing maxsize")
```

### Diagnosing Low Hit Rates

1. **Arguments not repeating**: Cache only helps if same args are called multiple times
2. **maxsize too small**: Cache evicting entries before they're reused
3. **Unhashable arguments**: Check if args are truly hashable

```python
# Debug: Track unique arguments
call_args = []

@lru_cache(maxsize=128)
def my_func(arg):
    call_args.append(arg)  # Track before caching
    return compute(arg)

# After workload:
unique_args = len(set(call_args))
total_calls = len(call_args)
print(f"Unique args: {unique_args} / Total calls: {total_calls}")
print(f"Potential hit rate: {(1 - unique_args/total_calls) * 100:.1f}%")
```

## Summary

| Method | Pros | Cons | Use When |
|--------|------|------|----------|
| **Production Profiling** | Accurate, real data, shows actual hit rates | Requires running app, needs representative workload | You can simulate typical usage |
| **Static Analysis** | No execution needed, fast, always works | Estimates only, can't measure hit rates | Quick analysis or can't run app |
| **Cache Stats Collection** | Direct cache metrics, precise hit rates | Must run after workload, need code access | Evaluating existing caches |
| **Continuous Monitoring** | Real production data, trends over time | Adds overhead, requires instrumentation | Production optimization |

**Recommendation**: Start with static analysis for quick wins, then use production profiling to validate and optimize further.

## See Also

- [Cache Subserver Documentation](CACHE_SUBSERVER.md) - Complete cache analysis reference
- [Getting Started](GETTING_STARTED.md) - Project overview
