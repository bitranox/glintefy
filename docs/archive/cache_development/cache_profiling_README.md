# Cache Profiling Documentation

## 📚 Documentation Index

This directory contains comprehensive documentation on how to profile your application and use profiling data for cache optimization.

### Quick Start

**New to cache profiling?** Start here:

1. **[Quick Reference](cache_profiling_quick_reference.md)** - Commands and common workflows (5 min read)
2. **[Full Guide](cache_profiling_guide.md)** - Complete profiling guide with examples (20 min read)

### Files

| Document | Purpose | Audience |
|----------|---------|----------|
| **[cache_profiling_quick_reference.md](cache_profiling_quick_reference.md)** | Quick commands, cheat sheet | Everyone - start here! |
| **[cache_profiling_guide.md](cache_profiling_guide.md)** | Detailed guide, best practices | Deep dive, troubleshooting |
| **[examples/profile_my_app_template.py](examples/profile_my_app_template.py)** | Copy-and-customize template | Custom profiling |

### Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **[scripts/profile_application.py](/scripts/profile_application.py)** | General-purpose profiler | `python scripts/profile_application.py --analyze` |
| **[examples/profile_my_app_template.py](examples/profile_my_app_template.py)** | Template for custom workloads | Copy, edit, run |

## Workflow Overview

```
┌─────────────────────┐
│  1. Profile App     │
│  (collect data)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  test_profile.prof  │  ← Profiling data saved here
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. Run Analysis    │
│  (evaluate caches)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. View Results    │
│  (recommendations)  │
└─────────────────────┘
```

## Two Analysis Modes

### Mode 1: Static Analysis (Default)

**No profiling needed** - analyzes code structure:

```bash
# Just run cache analysis
python -m glintefy review cache
```

**Pros:**
- ✅ Fast, no setup required
- ✅ Works on any codebase
- ✅ No application execution needed

**Cons:**
- ⚠️ Estimates only (counts call sites, not actual calls)
- ⚠️ Can't measure hit rates
- ⚠️ Misses runtime patterns (loops, conditional calls)

**Best for:** Quick analysis, exploration, codebases you can't run

### Mode 2: Profiling Data (Recommended)

**Profile real usage** - measures actual execution:

```bash
# 1. Profile application
python scripts/profile_application.py

# 2. Run cache analysis
python -m glintefy review cache
```

**Pros:**
- ✅ Accurate hit rates from real usage
- ✅ Shows actual runtime call counts
- ✅ Reveals performance hotspots
- ✅ Data-driven recommendations

**Cons:**
- ⚠️ Requires running your application
- ⚠️ Needs representative workload
- ⚠️ Takes more time

**Best for:** Production optimization, data-driven decisions, critical caches

## Example: Full Workflow

### Step 1: Create Profiling Script

```bash
cp docs/examples/profile_my_app_template.py profile_my_app.py
```

Edit `profile_my_app.py`:

```python
def run_my_workload():
    """CUSTOMIZE THIS: Your application's typical workload."""
    from my_app import process_files

    # Simulate realistic usage
    files = list(Path("data/sample").glob("*.csv"))
    process_files(files)
```

### Step 2: Run Profiling

```bash
python profile_my_app.py
```

Output:
```
Running workload...
✓ Workload complete

✓ Profiling data saved to: LLM-CONTEXT/glintefy/review/perf/test_profile.prof
```

### Step 3: Analyze Caches

```bash
python -m glintefy review cache
```

### Step 4: Review Results

```bash
cat LLM-CONTEXT/glintefy/review/cache/existing_cache_evaluations.json
```

Example output:

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

## Common Use Cases

### Use Case 1: "Should I cache this function?"

**Solution:** Run static analysis first:

```bash
python -m glintefy review cache
```

Look at pure function candidates. Then profile to validate.

### Use Case 2: "Are my existing caches working?"

**Solution:** Profile your application with real workload:

```bash
# Profile
python scripts/profile_application.py --workload my_app:main

# Analyze
python -m glintefy review cache
```

Check `existing_cache_evaluations.json` for hit rates.

### Use Case 3: "Optimize for production"

**Solution:** Profile production workload simulation:

```python
# profile_prod_workload.py
def simulate_production():
    """Replay production traffic patterns."""
    # Load sample of production data
    # Run typical operations
    # Hit realistic code paths
```

Then analyze with profiling data.

### Use Case 4: "CI/CD integration"

**Solution:** Add to GitHub Actions:

```yaml
- name: Profile and analyze caches
  run: |
    python scripts/profile_application.py
    python -m glintefy review cache

- name: Check for inefficient caches
  run: |
    python -c "
    import json
    with open('LLM-CONTEXT/glintefy/review/cache/existing_cache_evaluations.json') as f:
        evals = json.load(f)
        low_hit = [e for e in evals if e['hit_rate_percent'] < 10]
        if low_hit:
            print(f'⚠️  {len(low_hit)} caches with <10% hit rate')
            exit(1)
    "
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `python scripts/profile_application.py` | Profile test suite |
| `python -m glintefy review cache` | Run cache analysis |
| `python scripts/profile_application.py && python -m glintefy review cache` | Both in sequence |

## File Locations

```
project_root/
├── docs/
│   ├── cache_profiling_README.md           ← You are here
│   ├── cache_profiling_guide.md            ← Full guide
│   ├── cache_profiling_quick_reference.md  ← Quick reference
│   └── examples/
│       └── profile_my_app_template.py      ← Template
├── scripts/
│   └── profile_application.py              ← Profiling script
└── LLM-CONTEXT/
    └── glintefy/
        └── review/
            ├── perf/
            │   └── test_profile.prof       ← Profiling data (INPUT)
            └── cache/
                ├── existing_cache_evaluations.json  ← Results (OUTPUT)
                └── cache_analysis.json              ← Summary (OUTPUT)
```

## Next Steps

1. **Quick Start:** Read [Quick Reference](cache_profiling_quick_reference.md)
2. **Learn More:** Read [Full Guide](cache_profiling_guide.md)
3. **Get Profiling:** Copy [Template](examples/profile_my_app_template.py)
4. **Profile:** Run `python profile_my_app.py`
5. **Analyze:** Run `python -m glintefy review cache`
6. **Act:** Follow recommendations in results

## Getting Help

### Documentation

- **Quick commands:** [cache_profiling_quick_reference.md](cache_profiling_quick_reference.md)
- **Detailed guide:** [cache_profiling_guide.md](cache_profiling_guide.md)
- **Troubleshooting:** See "Troubleshooting" section in Full Guide

### Examples

- **Template:** [examples/profile_my_app_template.py](examples/profile_my_app_template.py)
- **CLI application:** See "Workflow 1" in Full Guide
- **Web application:** See "Workflow 2" in Full Guide
- **Data pipeline:** See "Workflow 3" in Full Guide

### Tools

- **Profiling script:** `python scripts/profile_application.py --help`
- **Cache analysis:** `python -m glintefy review cache --help`

## Summary

**Quick workflow:**
1. Copy template → Edit for your app → Run profiling
2. Run cache analysis
3. Review recommendations
4. Apply optimizations

**Or use static analysis** (no profiling):
```bash
python -m glintefy review cache
```

Start with static analysis for quick wins, then add profiling for precision.
