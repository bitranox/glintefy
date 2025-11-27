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

## Quick Start: 2-Step Workflow

### Step 1: Collect Profiling Data

Run your application with profiling enabled using your typical workload:

```python
import cProfile
import pstats
from pathlib import Path

# Profile your application
profiler = cProfile.Profile()
profiler.enable()

# Run your typical workload here
# Example: Process files, handle requests, run operations, etc.
run_your_application()

profiler.disable()

# Save profiling data
output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
output_dir.mkdir(parents=True, exist_ok=True)
profiler.dump_stats(output_dir / "test_profile.prof")

print(f"✓ Profiling data saved to {output_dir / 'test_profile.prof'}")
```

### Step 2: Run Cache Analysis

With profiling data available, cache analysis will automatically detect and use it:

```bash
python -m btx_fix_mcp review cache
```

Or via the MCP server:

```python
from btx_fix_mcp.servers.review import ReviewMCPServer

server = ReviewMCPServer(repo_path=".")
result = server.run_cache()
print(result["summary"])
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
        output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
        output_dir.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(output_dir / "test_profile.prof")

        print(f"\n✓ Profiling data saved", file=sys.stderr)
```

Run it:
```bash
python profile_my_app.py
python -m btx_fix_mcp review cache
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

    output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
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

    output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
```

### Workflow 4: Profile Test Suite

Use your test suite as a proxy for real usage:

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

    output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
```

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
<repo_root>/LLM-CONTEXT/btx_fix_mcp/review/perf/test_profile.prof
```

You can also specify a custom location when creating the cache sub-server:

```python
from btx_fix_mcp.subservers.review.cache_subserver import CacheSubServer
from pathlib import Path

server = CacheSubServer(
    output_dir=Path("LLM-CONTEXT/btx_fix_mcp/review/cache"),
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

    output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
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
python -m btx_fix_mcp review cache  # Analyze with fresh data
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

1. Verify file exists: `ls -la LLM-CONTEXT/btx_fix_mcp/review/perf/test_profile.prof`
2. Check file is valid: `python -c "import pstats; pstats.Stats('LLM-CONTEXT/btx_fix_mcp/review/perf/test_profile.prof').print_stats()"`
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
    output_dir = Path("LLM-CONTEXT/btx_fix_mcp/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print("✓ Profiling data saved")
EOF

# 2. Run profiling
python profile_app.py

# 3. Run cache analysis with profiling data
python -m btx_fix_mcp review cache

# 4. Review results
cat LLM-CONTEXT/btx_fix_mcp/review/cache/existing_cache_evaluations.json
```

## Summary

| Method | Pros | Cons | Use When |
|--------|------|------|----------|
| **Production Profiling** | Accurate, real data, shows actual hit rates | Requires running app, needs representative workload | You can simulate typical usage |
| **Static Analysis** | No execution needed, fast, always works | Estimates only, can't measure hit rates | Quick analysis or can't run app |

**Recommendation**: Start with static analysis for quick wins, then use production profiling to validate and optimize further.
