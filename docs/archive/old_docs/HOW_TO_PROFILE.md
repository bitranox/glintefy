# How to Profile Your Project for Cache Analysis

## The Easy Way (Recommended)

Just use the built-in `profile` command:

```bash
cd /your/project

# Profile any command
python -m glintefy review profile -- python my_app.py
python -m glintefy review profile -- pytest tests/
python -m glintefy review profile -- python -m my_module --args

# Then analyze
python -m glintefy review cache
```

That's it! No scripts to write, no code to copy.

---

## The Manual Way (If You Need More Control)

### Step 1: Create a profiling script in YOUR project

Create `profile.py` in your project root:

```python
import cProfile
from pathlib import Path

# Import and run YOUR application code
def run_your_app():
    """Replace this with your actual application code."""
    # Example 1: CLI app
    from my_app import main
    main()

    # Example 2: Process files
    # from my_pipeline import process_batch
    # process_batch(Path("data").glob("*.csv"))

    # Example 3: Web app simulation
    # from my_app import test_client
    # client = test_client()
    # for i in range(100):
    #     client.get(f"/api/items/{i}")

if __name__ == "__main__":
    # Start profiling
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your workload
    run_your_app()

    # Stop and save
    profiler.disable()

    # Save to the location glintefy expects
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")

    print(f"✓ Profile saved to {output_dir / 'test_profile.prof'}")
```

### Step 2: Run your profiling script

```bash
cd /your/project
python profile.py
```

### Step 3: Analyze caches with profiling data

```bash
cd /your/project
python -m glintefy review cache
```

That's it! glintefy will automatically detect and use your profiling data.

---

## Where Files Go

```
your-project/
├── profile.py                    ← You create this
├── your_app/
│   └── ...
└── LLM-CONTEXT/
    └── glintefy/
        └── review/
            ├── perf/
            │   └── test_profile.prof    ← Profile saved here
            └── cache/
                └── existing_cache_evaluations.json  ← Results here
```

---

## Real Examples

### Example 1: CLI Application

```python
# profile.py
import cProfile
from pathlib import Path
from my_cli_app import main
import sys

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your CLI with typical arguments
    sys.argv = ["my_cli_app", "--input", "data/sample.csv", "--output", "results/"]
    main()

    profiler.disable()
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")
    print("✓ Profile saved")
```

### Example 2: Web Application

```python
# profile.py
import cProfile
from pathlib import Path
from my_web_app import app

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Simulate realistic web traffic
    with app.test_client() as client:
        # Typical user flows
        for i in range(100):
            client.get(f"/api/users/{i}")
            client.post("/api/data", json={"key": f"value_{i}"})
            client.get(f"/api/search?q=query{i}")

    profiler.disable()
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")
    print("✓ Profile saved")
```

### Example 3: Data Processing Pipeline

```python
# profile.py
import cProfile
from pathlib import Path
from my_pipeline import process_files

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Process sample data (representative of production)
    files = list(Path("data/sample").glob("*.csv"))
    process_files(files)

    profiler.disable()
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")
    print("✓ Profile saved")
```

### Example 4: Test Suite (Fallback)

```python
# profile.py
import cProfile
from pathlib import Path
import pytest

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your test suite
    pytest.main(["tests/", "-v", "--tb=short"])

    profiler.disable()
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output_dir / "test_profile.prof")
    print("✓ Profile saved")
```

---

## What Happens

### Without Profile (Static Analysis Only)

```bash
cd /your/project
python -m glintefy review cache
```

**Output:**
```
⚠️  Using Static Code Analysis
No production profiling data available.
```

**Result:**
```json
{
  "function": "expensive_func",
  "recommendation": "KEEP",
  "reason": "Static analysis: Function called 5 times in codebase",
  "evidence": {"hits": 0, "misses": 0}
}
```

### With Profile (Production Data)

```bash
cd /your/project
python profile.py
python -m glintefy review cache
```

**Output:**
```
✅ Using Production Cache Data
Recommendations based on real cache statistics.
```

**Result:**
```json
{
  "function": "expensive_func",
  "recommendation": "KEEP",
  "reason": "Production data: Good hit rate (87.2%)",
  "evidence": {"hits": 2451, "misses": 359}
}
```

---

## Important Notes

### ✅ DO:
- **Use realistic data** - Profile with data similar to production
- **Run typical workload** - Simulate normal usage patterns
- **Run long enough** - Let caches warm up (not just startup code)
- **Use representative operations** - Cover the main code paths

### ❌ DON'T:
- **Don't use toy data** - Unrealistic data gives unrealistic results
- **Don't profile just tests** - Tests clear caches for isolation
- **Don't profile just initialization** - Caches need usage to show benefit
- **Don't use fake operations** - Profile real usage patterns

---

## Workflow Summary

```
┌─────────────────────────────────────┐
│ 1. Create profile.py in YOUR project│
│    (copy template above)            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 2. Edit run_your_app() to run      │
│    YOUR application                 │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 3. Run: python profile.py           │
│    → Saves to LLM-CONTEXT/.../perf/ │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 4. Run: python -m glintefy       │
│         review cache                │
│    → Reads profile automatically    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 5. View results in:                 │
│    LLM-CONTEXT/glintefy/         │
│    review/cache/*.json              │
└─────────────────────────────────────┘
```

---

## Troubleshooting

### "No profiling data found"

✅ **Expected!** glintefy will use static analysis.

To add profiling data:
1. Check file exists: `ls LLM-CONTEXT/glintefy/review/perf/test_profile.prof`
2. If missing, run `python profile.py`
3. Re-run cache analysis

### "All caches show 0% hit rate"

Your workload didn't call the cached functions. Make sure:
- ✅ Your `run_your_app()` actually uses the code with caches
- ✅ You're not just running initialization code
- ✅ The cached functions are actually called

### "Profile file is too large"

Large profiles are fine! They contain detailed call statistics.

If it's a problem:
- Profile a shorter workload
- Focus on key operations only
- Don't profile the entire multi-hour batch job

---

## Next Steps

1. **Create** `profile.py` in your project (copy template above)
2. **Edit** `run_your_app()` to run your application
3. **Run** `python profile.py`
4. **Analyze** `python -m glintefy review cache`
5. **Review** results in `LLM-CONTEXT/glintefy/review/cache/`

That's it! No complex setup, no external tools - just standard Python profiling.
