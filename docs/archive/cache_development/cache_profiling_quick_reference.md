# Cache Profiling Quick Reference

## Overview

The cache analysis system has **two modes**:

| Mode | Data Source | Accuracy | Use When |
|------|-------------|----------|----------|
| **Static Analysis** | Code analysis (call sites) | Estimates | Quick analysis, can't run app |
| **Profiling Data** | Real runtime execution | Accurate | Need precise hit rates |

## Quick Commands

### Option 1: Use Ready-Made Script

```bash
# Profile and analyze in one command
python scripts/profile_application.py --analyze
```

### Option 2: Custom Workload (Recommended)

```bash
# 1. Copy template
cp docs/examples/profile_my_app_template.py profile_my_app.py

# 2. Edit profile_my_app.py to run YOUR workload
#    (Replace run_my_workload() function)

# 3. Run profiling
python profile_my_app.py

# 4. Run analysis
python -m glintefy review cache
```

### Option 3: Profile Custom Module

```bash
# Profile specific function
python scripts/profile_application.py \
    --workload my_app.main:run_application \
    --analyze
```

## Where Files Go

```
your_project/
├── LLM-CONTEXT/
│   └── glintefy/
│       └── review/
│           ├── perf/
│           │   └── test_profile.prof  ← Profiling data goes here
│           └── cache/
│               ├── existing_cache_evaluations.json  ← Results here
│               └── cache_analysis.json
```

## Interpreting Results

### With Profiling Data (Best)

```json
{
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

✅ **Trustworthy** - Based on real usage

### Without Profiling Data (Estimates)

```json
{
  "function": "expensive_computation",
  "recommendation": "KEEP",
  "reason": "Static analysis: Function called 15 times in codebase",
  "evidence": {
    "hits": 0,
    "misses": 0,
    "hit_rate_percent": 0.0
  }
}
```

⚠️ **Approximate** - Based on code structure only

## Common Workflows

### Workflow: Web Application

```python
# profile_web_app.py
import cProfile
from pathlib import Path
from my_app import app, test_client

profiler = cProfile.Profile()
profiler.enable()

# Simulate realistic traffic
client = test_client()
for i in range(100):
    client.get(f"/api/items/{i}")
    client.post("/api/data", json={"key": f"value_{i}"})

profiler.disable()

# Save
output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
output_dir.mkdir(parents=True, exist_ok=True)
profiler.dump_stats(output_dir / "test_profile.prof")
```

### Workflow: Data Pipeline

```python
# profile_pipeline.py
import cProfile
from pathlib import Path
from my_pipeline import process_batch

profiler = cProfile.Profile()
profiler.enable()

# Run typical batch
files = list(Path("data/sample").glob("*.csv"))
process_batch(files)

profiler.disable()

# Save
output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
output_dir.mkdir(parents=True, exist_ok=True)
profiler.dump_stats(output_dir / "test_profile.prof")
```

## Troubleshooting

### "No profiling data found"

✅ **This is normal!** Cache analysis will use static analysis.

To add profiling data:
1. Run one of the profiling commands above
2. Re-run cache analysis

### "All caches show 0% hit rate"

This happens when:
- ❌ Profiling data wasn't created correctly
- ❌ Workload didn't call the cached functions
- ❌ Test suite calls `cache_clear()` (isolates tests)

Fix:
- Ensure your workload actually uses the cached functions
- Profile production-like usage, not just unit tests

### "Static analysis gives different result than profiling"

**Expected!** They measure different things:

```python
# Static analysis sees: 1 call site
for i in range(1000):
    result = cached_function(i)  # Runtime: 1000 calls!
```

- **Static analysis:** Counts call sites in code
- **Profiling:** Counts actual runtime calls

**Profiling is more accurate** for cache decisions.

## Best Practices

### ✅ DO:
- Profile with **realistic workloads**
- Use **production-like data** (anonymized if needed)
- Run **long enough** to hit steady state (not just startup)
- Profile **multiple scenarios** if usage varies

### ❌ DON'T:
- Profile only trivial examples
- Use fake/toy data that doesn't match production
- Profile just initialization code
- Rely solely on unit tests (they clear caches for isolation)

## Integration with CI/CD

```yaml
# .github/workflows/cache-analysis.yml
- name: Profile application
  run: python scripts/profile_application.py

- name: Analyze caches
  run: python -m glintefy review cache

- name: Upload results
  uses: actions/upload-artifact@v3
  with:
    name: cache-analysis
    path: LLM-CONTEXT/glintefy/review/cache/
```

## Next Steps

📚 **Full Documentation:** [docs/cache_profiling_guide.md](cache_profiling_guide.md)

🔍 **After Analysis:** Review recommendations in:
- `LLM-CONTEXT/glintefy/review/cache/existing_cache_evaluations.json`

🎯 **Take Action:**
- **REMOVE**: Delete `@lru_cache` decorators with low hit rates
- **KEEP**: Leave well-performing caches as-is
- **ADJUST**: Change `maxsize` parameter as suggested
