# Cache Profiling - Complete Implementation

## Quick Start

### For Users (No Code Required!)

```bash
cd /your/project

# Option 1: Static analysis (fast, estimates)
python -m glintefy review cache

# Option 2: With profiling (accurate, real data)
python -m glintefy review profile -- python my_app.py
python -m glintefy review cache
```

That's it!

---

## What You Get

### Without Profiling (Static Analysis)

```
⚠️  Using Static Code Analysis

No production profiling data available. Recommendations based on static code
analysis.

                💡 Get More Accurate Results with Profiling Data

Profile your application with a single command:


 # Profile any command
 python -m glintefy review profile -- python my_app.py
 python -m glintefy review profile -- pytest tests/
 python -m glintefy review profile -- python -m my_module

 # Then analyze caches
 python -m glintefy review cache
```

**Results:**
- ✅ Instant analysis (no setup)
- ✅ Call frequency estimates
- ✅ REMOVE/KEEP recommendations
- ⚠️ No hit rate data

### With Profiling (Production Data)

```
✅ Using Production Cache Data

Recommendations based on real cache statistics from your application.
```

**Results:**
- ✅ Accurate hit rates
- ✅ Real usage patterns
- ✅ Data-driven recommendations
- ✅ Performance metrics

---

## Examples

### Example 1: Profile a Script

```bash
cd /your/project
python -m glintefy review profile -- python main.py
python -m glintefy review cache
```

### Example 2: Profile Tests

```bash
cd /your/project
python -m glintefy review profile -- pytest tests/
python -m glintefy review cache
```

### Example 3: Profile with Arguments

```bash
cd /your/project
python -m glintefy review profile -- python app.py --input data.csv --workers 4
python -m glintefy review cache
```

### Example 4: Profile a Module

```bash
cd /your/project
python -m glintefy review profile -- python -m my_package.cli
python -m glintefy review cache
```

---

## Output Example

### Static Analysis Results

```
                           Existing Cache Evaluation

 • Keep: 2 caches performing well
 • Remove: 2 caches with low hit rates
 • Adjust: 0 caches with suboptimal maxsize

                             Remove (Low Hit Rate)

                 _get_cached_classification (llm_client.py:525)

 • Current: @lru_cache(maxsize=1000)
 • Hit rate: 0.0%
 • Recommendation: Static analysis: Function called only 1 time in codebase -
   no cache benefit

                        get_cache_dir (tools_venv.py:51)

 • Current: @lru_cache(maxsize=1)
 • Hit rate: 0.0%
 • Recommendation: Static analysis: Function called only 1 time in codebase -
   no cache benefit

                             Keep (Performing Well)

 • get_venv_path (tools_venv.py:67): Called 6 times in codebase
 • get_tool_path (tools_venv.py:73): Called 16 times in codebase

Metrics:
  pure_functions: 1336
  existing_caches: 4
  existing_keep: 2
  existing_remove: 2
```

---

## Implementation Details

### What Was Built

1. **Static Code Analysis** (batch_screener.py:119-178)
   - Scans Python files for function calls
   - Counts call sites (excluding tests)
   - Recommends REMOVE (≤1 calls) or KEEP (≥2 calls)

2. **Hybrid Approach** (batch_screener.py:272-417)
   - Checks for production cache statistics first
   - Falls back to static analysis if no data
   - Clearly labels analysis method in results

3. **Profile Command** (cli.py:293-343)
   - `python -m glintefy review profile -- <command>`
   - Wraps command execution with cProfile
   - Saves to expected location automatically
   - Shows next steps

4. **Auto-Detection** (cache_subserver.py:216-234)
   - Looks for profile at `LLM-CONTEXT/glintefy/review/perf/test_profile.prof`
   - Uses profiling data if available
   - Falls back to static analysis otherwise

### Files Created/Modified

**New Files:**
- `docs/HOW_TO_PROFILE.md` - User guide with examples
- `docs/cache_profiling_guide.md` - Detailed profiling workflows
- `docs/cache_profiling_quick_reference.md` - Quick commands
- `docs/cache_profiling_README.md` - Documentation index
- `docs/CACHE_PROFILING_COMPLETE.md` - This file

**Modified Files:**
- `src/glintefy/cli.py` - Added `review profile` command
- `src/glintefy/subservers/review/cache_subserver.py` - Updated instructions
- `src/glintefy/subservers/review/cache/batch_screener.py` - Static analysis
- `src/glintefy/subservers/review/cache/pure_function_detector.py` - Removed private method filter

### Technical Architecture

```
User Command
    │
    ├─> python -m glintefy review profile -- <cmd>
    │   │
    │   ├─> Wraps command with cProfile
    │   ├─> Runs command
    │   └─> Saves profile.prof
    │
    └─> python -m glintefy review cache
        │
        ├─> Load existing caches
        │
        ├─> Check for profile.prof
        │   │
        │   ├─> If found: Use production data
        │   │   └─> Get cache_info() stats
        │   │
        │   └─> If not found: Use static analysis
        │       └─> Count call sites in code
        │
        └─> Generate recommendations
```

---

## Benefits

### For Users

1. **Zero Barrier** - Works immediately with static analysis
2. **Simple Profiling** - One command, no code to write
3. **Clear Guidance** - Reports explain how to improve accuracy
4. **Flexible** - Choose speed (static) or accuracy (profiling)
5. **Actionable** - Clear REMOVE/KEEP/ADJUST recommendations

### For Developers

1. **Clean Design** - Hybrid approach with clear fallback
2. **Testable** - Both modes tested independently
3. **Extensible** - Easy to add more analysis methods
4. **Documented** - Comprehensive user and dev documentation
5. **Integrated** - Works seamlessly with existing review tools

---

## Comparison

| Feature | Static Analysis | Profiling Data |
|---------|----------------|----------------|
| **Setup Required** | None | Run `profile` command |
| **Speed** | Instant | Depends on workload |
| **Accuracy** | Estimates | Precise |
| **Hit Rates** | No | Yes |
| **Call Counts** | Code-based | Runtime-based |
| **Best For** | Quick wins, exploration | Production optimization |

---

## Use Cases

### Use Case 1: "Should I cache this?"
**Answer:** Run static analysis to see if function is called multiple times

```bash
python -m glintefy review cache
```

### Use Case 2: "Are my caches working?"
**Answer:** Profile your app to see real hit rates

```bash
python -m glintefy review profile -- python my_app.py
python -m glintefy review cache
```

### Use Case 3: "Quick code review"
**Answer:** Static analysis is instant

```bash
python -m glintefy review cache
```

### Use Case 4: "Production optimization"
**Answer:** Profile realistic workload

```bash
python -m glintefy review profile -- pytest tests/ --workers 4
python -m glintefy review cache
```

---

## Next Steps

1. **Read** `docs/HOW_TO_PROFILE.md` for examples
2. **Try** static analysis: `python -m glintefy review cache`
3. **Profile** your app: `python -m glintefy review profile -- <command>`
4. **Apply** recommendations from results

---

## Summary

✅ **Easy** - One command, no code required
✅ **Fast** - Static analysis works instantly
✅ **Accurate** - Profiling gives real data when needed
✅ **Actionable** - Clear recommendations
✅ **Integrated** - Part of standard review workflow

Cache profiling is now production-ready and user-friendly!
